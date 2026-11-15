import urllib.request
import json

def test():
    with urllib.request.urlopen("http://127.0.0.1:8000/health") as r:
        print("HEALTH:", json.loads(r.read())["status"])

    with urllib.request.urlopen("http://127.0.0.1:8000/api/signals/agent/status") as r:
        s = json.loads(r.read())
        print(f"AGENT: active={s['active_approach']} phase={s['phase_state']} remaining={s['phase_remaining_seconds']}s")
        for k, v in s["approaches"].items():
            print(f"  {k:5}: lamp={v['color']} countdown={v['countdown_seconds']}s veh={v['telemetry']['vehicles']} density={v['telemetry']['density']}%")

    with urllib.request.urlopen("http://127.0.0.1:8000/api/dashboard/charts") as r:
        ch = json.loads(r.read())
        print("CHARTS volume points:", len(ch["volume_trend"]["volumes"]), "density points:", len(ch["density_trend"]["densities"]))

if __name__ == "__main__":
    test()

