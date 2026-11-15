with open('frontend/pages/database-admin.html', encoding='utf-8') as f:
    html = f.read()

used_ids = [
  'dap-kpi-tables',
  'dap-kpi-records',
  'dap-kpi-size',
  'dap-kpi-ver',
  'dap-kpi-pages',
  'dap-kpi-journal',
  'dap-tables-list',
  'dap-current-table-label',
  'dap-insert-table-name',
  'dap-export-table-title',
  'dap-export-meta-table',
  'dap-row-search-input',
  'dap-export-meta-pk',
  'dap-export-meta-count',
  'dap-table-thead',
  'dap-table-tbody',
  'dap-browse-total-label',
  'dap-page-indicator',
  'btn-page-prev',
  'btn-page-next',
  'dap-per-page-select',
  'dap-schema-tbody',
  'dap-create-sql-box',
  'dap-insert-fields-container',
  'dap-insert-form',
  'dap-edit-modal',
  'dap-edit-modal-title',
  'dap-edit-fields-container',
  'dap-edit-form',
  'dap-view-modal',
  'dap-view-json-content',
  'btn-run-sql',
  'dap-sql-input',
  'dap-sql-stats-banner',
  'dap-sql-thead',
  'dap-sql-tbody',
  'btn-vacuum-db',
  'btn-integrity-check',
  'btn-download-db',
  'btn-export-csv',
  'btn-export-json',
  'dap-table-search-input',
  'btn-refresh-tables'
]

missing = [i for i in used_ids if f'id="{i}"' not in html]
print('Missing IDs in HTML:', missing)

