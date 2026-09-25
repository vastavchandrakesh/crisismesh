"""
CrisisMesh Device Simulator
Simulates multiple phones sending distress signals to the backend.
Usage: python device_simulator.py [--base-url http://localhost:8000] [--zone-id <id>]
"""
import requests
import time
import argparse
import random

BASE_URL = "http://localhost:8000"

SCENARIOS = [
    # (device_id, transcript, event_type_hint, lat_offset, lon_offset)
    ("phone_A", "HELP! HELP! I am trapped under rubble!", "verbal_distress", 0.0001,  0.0002),
    ("phone_B", "I am trapped, please send rescue immediately", "verbal_distress", 0.0002, 0.0001),
    ("phone_C", "knocking knocking knocking", "knocking",  0.0001, 0.0003),
    ("phone_D", "background noise wind",     "ambient_noise", 0.5000, 0.5000),  # far away
    ("phone_E", "someone please hear me, I can't move", "verbal_distress", 0.0002, 0.0002),
]

BASE_LAT = 12.9716
BASE_LON = 77.5946


def simulate(zone_id: str, base_url: str = BASE_URL):
    print(f"\n[Simulator] Starting with zone_id={zone_id}, backend={base_url}\n")

    for device_id, transcript, evt_type, dlat, dlon in SCENARIOS:
        # grant consent
        resp = requests.post(f"{base_url}/api/devices/consent", json={
            "device_id": device_id,
            "zone_id": zone_id,
        })
        if resp.status_code == 201:
            print(f"  [consent] {device_id} opted in")
        else:
            print(f"  [consent] {device_id} FAILED: {resp.text}")

    print()
    for device_id, transcript, evt_type, dlat, dlon in SCENARIOS:
        payload = {
            "device_id":       device_id,
            "zone_id":         zone_id,
            "transcript":      transcript,
            "event_type_hint": evt_type,
            "lat":             BASE_LAT + dlat,
            "lon":             BASE_LON + dlon,
        }
        resp = requests.post(f"{base_url}/api/events", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            cls  = data["classification"]
            print(
                f"  [event] {device_id:10s} | {evt_type:18s} | "
                f"confidence={cls['confidence']:.2f} | priority={cls['priority']:8s} | "
                f"incident={data.get('incident_id','—')[:8] if data.get('incident_id') else '—'}"
            )
        else:
            print(f"  [event] {device_id} ERROR: {resp.text}")
        time.sleep(0.3)

    print("\n[Simulator] Simulating offline scenario for phone_F...")
    # phone_F goes offline, queues events, then syncs
    offline_events = [
        {
            "device_id":       "phone_F",
            "zone_id":         zone_id,
            "transcript":      "I'm here please help, stuck in basement",
            "event_type_hint": "verbal_distress",
            "lat":             BASE_LAT + 0.0001,
            "lon":             BASE_LON + 0.0002,
            "offline_flag":    True,
        }
    ]
    # grant consent for phone_F first
    requests.post(f"{base_url}/api/devices/consent", json={"device_id": "phone_F", "zone_id": zone_id})

    resp = requests.post(f"{base_url}/api/offline/sync", json={
        "device_id": "phone_F",
        "events":    offline_events,
    })
    data = resp.json()
    print(f"  [offline-sync] synced={data['synced']} results={data['results'][0]['status']}")

    print("\n[Simulator] Done. Check the dashboard for incidents.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--zone-id",  required=False, default=None)
    args = parser.parse_args()

    zone_id = args.zone_id
    if not zone_id:
        try:
            resp = requests.get(f"{args.base_url}/api/zones", timeout=5)
            zones = resp.json() if resp.status_code == 200 else []
        except Exception:
            zones = []
        if zones:
            zone_id = zones[0]["id"]
            print(f"[Simulator] Using existing zone: {zone_id} ({zones[0]['name']})")
        else:
            resp = requests.post(f"{args.base_url}/api/zones", json={
                "name": "Demo Zone Alpha",
                "lat": BASE_LAT,
                "lon": BASE_LON,
                "radius_m": 3000,
            }, timeout=5)
            zone_id = resp.json()["id"]
            print(f"[Simulator] Created zone: {zone_id}")

    simulate(zone_id, args.base_url)
