import os
import time
import math
import csv
import io
import json
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse

from app.config import settings

router = APIRouter(prefix="/api/db-admin", tags=["Database Admin (DAP)"])

def get_db_path() -> str:
    """Returns absolute path to the active SQLite database."""
    return str(settings.BASE_DIR / "traffic_system.db")

def get_sqlite_conn() -> sqlite3.Connection:
    """Creates a direct sqlite3 connection with Row factory."""
    conn = sqlite3.connect(get_db_path(), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def validate_table_name(table_name: str, conn: sqlite3.Connection) -> str:
    """Validates that table_name exists to prevent SQL injection."""
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'view') AND name = ?", (table_name,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist in the database.")
    return table_name

def get_table_pk(table_name: str, conn: sqlite3.Connection) -> str:
    """Finds the primary key column for a given table."""
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    cols = cur.fetchall()
    for col in cols:
        if col["pk"] == 1:
            return col["name"]
    # Fallback to 'id' or first column
    return cols[0]["name"] if cols else "id"


# =============================================================================
# 1. DATABASE OVERVIEW & METRICS
# =============================================================================

@router.get("/overview")
def get_database_overview():
    """
    Returns full database overview: file size, page stats, SQLite version,
    and all registered tables with live row and column counts.
    """
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found.")

    file_size_bytes = os.path.getsize(db_path)
    file_size_kb = round(file_size_bytes / 1024.0, 2)
    file_size_mb = round(file_size_bytes / (1024.0 * 1024.0), 3)

    conn = get_sqlite_conn()
    try:
        cur = conn.cursor()

        # PRAGMA system variables
        cur.execute("SELECT sqlite_version()")
        sqlite_ver = cur.fetchone()[0]

        cur.execute("PRAGMA page_size")
        page_size = cur.fetchone()[0]

        cur.execute("PRAGMA page_count")
        page_count = cur.fetchone()[0]

        cur.execute("PRAGMA journal_mode")
        journal_mode = cur.fetchone()[0].upper()

        cur.execute("PRAGMA encoding")
        encoding = cur.fetchone()[0]

        # Tables metadata
        cur.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name ASC
        """)
        table_records = cur.fetchall()

        tables = []
        total_rows_all = 0

        for rec in table_records:
            tname = rec["name"]
            tsql = rec["sql"]

            # Row count
            cur.execute(f"SELECT COUNT(*) FROM {tname}")
            row_count = cur.fetchone()[0]
            total_rows_all += row_count

            # Columns
            cur.execute(f"PRAGMA table_info({tname})")
            col_rows = cur.fetchall()
            columns = [
                {
                    "cid": c["cid"],
                    "name": c["name"],
                    "type": c["type"],
                    "notnull": bool(c["notnull"]),
                    "dflt_value": c["dflt_value"],
                    "pk": bool(c["pk"])
                }
                for c in col_rows
            ]

            pk_col = next((c["name"] for c in columns if c["pk"]), columns[0]["name"] if columns else "id")

            tables.append({
                "name": tname,
                "row_count": row_count,
                "column_count": len(columns),
                "columns": columns,
                "primary_key": pk_col,
                "create_sql": tsql
            })

        return {
            "database_name": os.path.basename(db_path),
            "database_path": db_path,
            "sqlite_version": sqlite_ver,
            "file_size_bytes": file_size_bytes,
            "file_size_kb": file_size_kb,
            "file_size_mb": file_size_mb,
            "page_size": page_size,
            "page_count": page_count,
            "journal_mode": journal_mode,
            "encoding": encoding,
            "total_tables": len(tables),
            "total_records": total_rows_all,
            "tables": tables,
            "integrity": "ok",
            "server_time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
    finally:
        conn.close()


# =============================================================================
# 2. TABLE SCHEMA & METADATA
# =============================================================================

@router.get("/tables/{table_name}/schema")
def get_table_schema(table_name: str):
    """Returns detailed schema, columns, indexes, and foreign keys for a specific table."""
    conn = get_sqlite_conn()
    try:
        validate_table_name(table_name, conn)
        cur = conn.cursor()

        # Columns
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = [dict(c) for c in cur.fetchall()]

        # Indexes
        cur.execute(f"PRAGMA index_list({table_name})")
        indexes = [dict(i) for i in cur.fetchall()]

        # Foreign keys
        cur.execute(f"PRAGMA foreign_key_list({table_name})")
        foreign_keys = [dict(fk) for fk in cur.fetchall()]

        # DDL
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name = ?", (table_name,))
        sql_row = cur.fetchone()
        create_sql = sql_row["sql"] if sql_row else ""

        pk_col = get_table_pk(table_name, conn)

        return {
            "table_name": table_name,
            "primary_key": pk_col,
            "columns": cols,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
            "create_sql": create_sql
        }
    finally:
        conn.close()


# =============================================================================
# 3. BROWSE / PAGINATE TABLE DATA
# =============================================================================

@router.get("/tables/{table_name}/data")
def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    search: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    order: str = Query("DESC")
):
    """
    Returns paginated rows for a table with optional multi-column search,
    sorting, and total counts.
    """
    conn = get_sqlite_conn()
    try:
        validate_table_name(table_name, conn)
        cur = conn.cursor()

        # Safe extraction whether called by FastAPI or directly in python
        page_val = int(page.default if hasattr(page, "default") else page)
        limit_val = int(limit.default if hasattr(limit, "default") else limit)
        search_val = search.default if hasattr(search, "default") else search
        sort_val = sort_by.default if hasattr(sort_by, "default") else sort_by
        order_val = str(order.default if hasattr(order, "default") else order).upper()

        # Retrieve table columns
        cur.execute(f"PRAGMA table_info({table_name})")
        cols_info = cur.fetchall()
        column_names = [c["name"] for c in cols_info]
        pk_name = get_table_pk(table_name, conn)

        # Validate sort column
        if sort_val and sort_val not in column_names:
            sort_val = pk_name
        if not sort_val:
            sort_val = pk_name

        sort_order = "ASC" if order_val == "ASC" else "DESC"

        # Build WHERE clause if search query exists
        where_clauses = []
        params = []
        if search_val and str(search_val).strip():
            kw = f"%{str(search_val).strip()}%"
            or_parts = []
            for col in column_names:
                or_parts.append(f"CAST({col} AS TEXT) LIKE ?")
                params.append(kw)
            where_clauses.append(f"({' OR '.join(or_parts)})")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count query
        count_sql = f"SELECT COUNT(*) FROM {table_name} {where_sql}"
        cur.execute(count_sql, params)
        total_rows = cur.fetchone()[0]

        total_pages = max(1, math.ceil(total_rows / limit_val))
        current_page = min(page_val, total_pages)
        offset = (current_page - 1) * limit_val

        # Data query
        data_sql = f"SELECT * FROM {table_name} {where_sql} ORDER BY {sort_val} {sort_order} LIMIT ? OFFSET ?"
        data_params = params + [limit_val, offset]

        cur.execute(data_sql, data_params)
        raw_rows = cur.fetchall()

        rows = []
        for r in raw_rows:
            row_dict = {}
            for col in column_names:
                val = r[col]
                row_dict[col] = val
            rows.append(row_dict)

        return {
            "table_name": table_name,
            "primary_key": pk_name,
            "columns": column_names,
            "rows": rows,
            "total_rows": total_rows,
            "page": current_page,
            "limit": limit_val,
            "total_pages": total_pages,
            "sort_by": sort_val,
            "order": sort_order
        }
    finally:
        conn.close()


# =============================================================================
# 4. CRUD: INSERT, UPDATE, DELETE ROWS
# =============================================================================

@router.post("/tables/{table_name}/rows")
def insert_table_row(table_name: str, payload: Dict[str, Any] = Body(...)):
    """Inserts a new row into the specified table."""
    conn = get_sqlite_conn()
    try:
        validate_table_name(table_name, conn)
        cur = conn.cursor()

        # Columns
        cur.execute(f"PRAGMA table_info({table_name})")
        cols_info = cur.fetchall()
        valid_cols = [c["name"] for c in cols_info]
        pk_name = get_table_pk(table_name, conn)

        # Filter payload for valid columns
        insert_data = {}
        for k, v in payload.items():
            if k in valid_cols:
                # If primary key is empty or null, omit to let SQLite auto-increment
                if k == pk_name and (v is None or v == "" or v == 0):
                    continue
                insert_data[k] = v

        if not insert_data:
            raise HTTPException(status_code=400, detail="No valid column values provided for insert.")

        col_keys = list(insert_data.keys())
        col_placeholders = [f":{k}" for k in col_keys]

        sql = f"INSERT INTO {table_name} ({', '.join(col_keys)}) VALUES ({', '.join(col_placeholders)})"
        cur.execute(sql, insert_data)
        conn.commit()

        new_row_id = cur.lastrowid
        return {
            "status": "success",
            "message": f"New record inserted successfully into '{table_name}'.",
            "row_id": new_row_id
        }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Insert failed: {str(e)}")
    finally:
        conn.close()


@router.put("/tables/{table_name}/rows/{row_id}")
def update_table_row(table_name: str, row_id: Any, payload: Dict[str, Any] = Body(...)):
    """Updates an existing record in the table by its primary key."""
    conn = get_sqlite_conn()
    try:
        validate_table_name(table_name, conn)
        cur = conn.cursor()

        cur.execute(f"PRAGMA table_info({table_name})")
        cols_info = cur.fetchall()
        valid_cols = [c["name"] for c in cols_info]
        pk_name = get_table_pk(table_name, conn)

        set_clauses = []
        update_data = {"__pk_val__": row_id}

        for k, v in payload.items():
            if k in valid_cols and k != pk_name:
                set_clauses.append(f"{k} = :{k}")
                update_data[k] = v

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No modifiable fields provided for update.")

        sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {pk_name} = :__pk_val__"
        cur.execute(sql, update_data)
        conn.commit()

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Record with {pk_name}={row_id} not found.")

        return {
            "status": "success",
            "message": f"Record #{row_id} in '{table_name}' updated successfully.",
            "rows_affected": cur.rowcount
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")
    finally:
        conn.close()


@router.delete("/tables/{table_name}/rows/{row_id}")
def delete_table_row(table_name: str, row_id: Any):
    """Deletes a record from the table by its primary key."""
    conn = get_sqlite_conn()
    try:
        validate_table_name(table_name, conn)
        cur = conn.cursor()
        pk_name = get_table_pk(table_name, conn)

        sql = f"DELETE FROM {table_name} WHERE {pk_name} = ?"
        cur.execute(sql, (row_id,))
        conn.commit()

        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Record with {pk_name}={row_id} not found.")

        return {
            "status": "success",
            "message": f"Record #{row_id} successfully deleted from '{table_name}'.",
            "rows_affected": cur.rowcount
        }
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"Delete failed: {str(e)}")
    finally:
        conn.close()


# =============================================================================
# 5. RAW SQL CONSOLE RUNNER
# =============================================================================

@router.post("/query")
def execute_raw_sql(payload: Dict[str, Any] = Body(...)):
    """
    Executes raw SQL query (SELECT, INSERT, UPDATE, DELETE, PRAGMA)
    and returns tabular results with execution time in milliseconds.
    """
    raw_query = payload.get("sql", "").strip()
    if not raw_query:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")

    conn = get_sqlite_conn()
    start_time = time.perf_counter()

    try:
        cur = conn.cursor()
        cur.execute(raw_query)
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        # Check if query returned rows (e.g. SELECT or PRAGMA)
        if cur.description:
            columns = [d[0] for d in cur.description]
            raw_rows = cur.fetchmany(500)
            rows = []
            for r in raw_rows:
                rows.append([r[col] for col in columns])

            return {
                "type": "SELECT",
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": elapsed_ms,
                "truncated": len(rows) == 500
            }
        else:
            conn.commit()
            return {
                "type": "EXECUTE",
                "message": "Query executed successfully.",
                "rows_affected": cur.rowcount,
                "execution_time_ms": elapsed_ms
            }
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=f"SQL Error: {str(e)}")
    finally:
        conn.close()


# =============================================================================
# 6. MAINTENANCE: VACUUM & INTEGRITY CHECK
# =============================================================================

@router.post("/vacuum")
def vacuum_database():
    """Executes SQLite VACUUM to reclaim free pages and defragment database file."""
    db_path = get_db_path()
    size_before = os.path.getsize(db_path)

    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    start_time = time.perf_counter()
    try:
        conn.execute("VACUUM")
        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        size_after = os.path.getsize(db_path)
        saved_bytes = max(0, size_before - size_after)

        return {
            "status": "success",
            "message": "SQLite database vacuumed and optimized successfully.",
            "execution_time_ms": elapsed_ms,
            "size_before_kb": round(size_before / 1024.0, 2),
            "size_after_kb": round(size_after / 1024.0, 2),
            "reclaimed_kb": round(saved_bytes / 1024.0, 2)
        }
    finally:
        conn.close()


@router.get("/integrity-check")
def run_integrity_check():
    """Runs PRAGMA integrity_check to verify database file health."""
    conn = get_sqlite_conn()
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA integrity_check")
        rows = [r[0] for r in cur.fetchall()]
        is_healthy = rows == ["ok"]
        return {
            "status": "HEALTHY" if is_healthy else "CORRUPTED",
            "messages": rows
        }
    finally:
        conn.close()


# =============================================================================
# 7. EXPORT TABLE & DOWNLOAD DB BACKUP
# =============================================================================

@router.get("/export/{table_name}")
def export_table(table_name: str, format: str = Query("csv", pattern="^(csv|json)$")):
    """Exports all rows from a table into CSV or JSON."""
    conn = get_sqlite_conn()
    try:
        validate_table_name(table_name, conn)
        cur = conn.cursor()
        cur.execute(f"SELECT * FROM {table_name}")
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()

        if format == "json":
            data = [{col: r[col] for col in cols} for r in rows]
            return JSONResponse(
                content=data,
                headers={"Content-Disposition": f"attachment; filename={table_name}_{int(time.time())}.json"}
            )
        else:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(cols)
            for r in rows:
                writer.writerow([r[col] for col in cols])
            output.seek(0)
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={table_name}_{int(time.time())}.csv"}
            )
    finally:
        conn.close()


@router.get("/download-db")
def download_database_file():
    """Downloads the actual SQLite database file as backup."""
    db_path = get_db_path()
    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file does not exist.")
    return FileResponse(
        db_path,
        media_type="application/x-sqlite3",
        filename=f"traffic_system_backup_{int(time.time())}.db"
    )
