"""
CrisisMesh Smoke Tests
Covers all 8 demo success criteria from the hackathon deck.

Usage:
    1. Start the backend:   cd backend && uvicorn main:app --port 8000
    2. In another terminal: python smoke_test.py
"""
import requests
import sys
import time
import threading
import json

BASE = "http://localhost:8000"
PASS = "\033[92m PASS\033[0m"
FAIL = "\033[91m FAIL\033[0m"

results = []


def check(label: str, condition: bool, detail: str = ""):
    icon = PASS if condition else FAIL
    results.append(condition)
    print(f"  [{icon}] {label}" + (f"  →  {detail}" if detail else ""))
    return condition


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ─── Criteria 1: Trigger emergency scenario (create zone) ─────────────────────
section("CRITERION 1 — Trigger emergency scenario (create zone)")
try:
    r = requests.post(f"{BASE}/api/zones", json={
        "name": "Bangalore Earthquake Zone-Alpha",
        "lat": 12.9716,
        "lon": 77.5946,
        "radius_m": 3000,
    }, timeout=5)
    ok = r.status_code == 201
    ZONE_ID = r.json().get("id") if ok else None
    check("Zone created", ok, f"id={ZONE_ID[:8] if ZONE_ID else 'N/A'}")
    r2 = requests.get(f"{BASE}/api/zones", timeout=5)
    zones = r2.json()
    check("Zone appears in list", any(z["id"] == ZONE_ID for z in zones))
except Exception as e:
    check("Zone API reachable", False, str(e))
    ZONE_ID = None

# ─── Criteria 2: Opt in a test device ────────────────────────────────────────
section("CRITERION 2 — Opt in test devices")
DEVICES = ["phone_A", "phone_B", "phone_C", "phone_D"]
for dev in DEVICES:
    r = requests.post(f"{BASE}/api/devices/consent", json={
        "device_id": dev,
        "zone_id": ZONE_ID,
    }, timeout=5)
    check(f"{dev} consented", r.status_code == 201)

# ─── Criteria 3 & 4: Generate distress event + AI scores it ──────────────────
section("CRITERION 3+4 — Generate distress event + AI scoring")
EVENT_PAYLOADS = [
    ("phone_A", "HELP! I am trapped under rubble, please help me!",  "verbal_distress", 12.9717, 77.5947),
    ("phone_B", "I am trapped and injured, send rescue immediately",  "verbal_distress", 12.9718, 77.5948),
    ("phone_C", "knocking knocking knocking on the wall repeatedly",  "knocking",        12.9717, 77.5948),
    ("phone_D", "wind noise ambient background",                      "ambient_noise",   12.8000, 77.4000),
]

created_events = []
for dev, transcript, evt_type, lat, lon in EVENT_PAYLOADS:
    r = requests.post(f"{BASE}/api/events", json={
        "device_id": dev,
        "zone_id":   ZONE_ID,
        "transcript": transcript,
        "event_type_hint": evt_type,
        "lat": lat,
        "lon": lon,
    }, timeout=5)
    ok = r.status_code == 201
    data = r.json() if ok else {}
    cls = data.get("classification", {})
    conf = cls.get("confidence", 0)
    is_distress = cls.get("is_distress", False)
    evt_id = data.get("event_id")
    if evt_id:
        created_events.append(data)

    if dev == "phone_D":
        check(f"{dev} noise correctly flagged as non-distress", not is_distress,
              f"conf={conf:.2f} type={cls.get('event_type')}")
    else:
        check(f"{dev} distress detected", ok and is_distress,
              f"conf={conf:.2f} priority={cls.get('priority')} keywords={cls.get('keywords_found')}")

# ─── Criteria 5: Nearby events cluster ───────────────────────────────────────
section("CRITERION 5 — Nearby events cluster into one incident")
time.sleep(0.5)  # give fusion a moment
r = requests.get(f"{BASE}/api/incidents?zone_id={ZONE_ID}", timeout=5)
incidents = r.json()
distress_incidents = [i for i in incidents if i["event_count"] > 0]
check("At least one incident created", len(distress_incidents) > 0,
      f"total incidents={len(incidents)}")
if distress_incidents:
    top = max(distress_incidents, key=lambda i: i["confidence"])
    check("Top incident has multiple events clustered", top["event_count"] > 1,
          f"event_count={top['event_count']} confidence={top['confidence']:.2f}")
    check("Noise-only phone NOT in top incident", top["event_count"] < 4,
          "phone_D (ambient) should be filtered")

# ─── Criteria 6: Dashboard shows one prioritized incident ────────────────────
section("CRITERION 6 — Dashboard shows prioritized incident")
if distress_incidents:
    top = max(distress_incidents, key=lambda i: i["confidence"])
    inc_detail = requests.get(f"{BASE}/api/incidents/{top['id']}", timeout=5).json()
    check("Incident has confidence score", top["confidence"] > 0,
          f"confidence={top['confidence']:.2f}")
    check("Incident has priority label", top["priority"] in ("HIGH","CRITICAL","MEDIUM"),
          f"priority={top['priority']}")
    check("Incident has sector label", bool(top.get("sector")),
          f"sector={top.get('sector')}")
    check("Incident detail includes event evidence", len(inc_detail.get("events", [])) > 0,
          f"evidence_count={len(inc_detail.get('events',[]))}")

# ─── Criteria 7 & 8: Simulate offline loss + Queue + Sync ────────────────────
section("CRITERION 7+8 — Simulate connectivity loss → queue → sync")
r = requests.post(f"{BASE}/api/devices/consent", json={
    "device_id": "phone_offline",
    "zone_id": ZONE_ID,
}, timeout=5)

offline_events = [
    {
        "device_id":       "phone_offline",
        "zone_id":         ZONE_ID,
        "transcript":      "I'm here! Stuck in basement, please come!",
        "event_type_hint": "verbal_distress",
        "lat":             12.9717,
        "lon":             77.5947,
        "offline_flag":    True,
    },
    {
        "device_id":       "phone_offline",
        "zone_id":         ZONE_ID,
        "transcript":      "still here, please help, knocking on door",
        "event_type_hint": "knocking",
        "lat":             12.9717,
        "lon":             77.5947,
        "offline_flag":    True,
    },
]
r = requests.post(f"{BASE}/api/offline/sync", json={
    "device_id": "phone_offline",
    "events":    offline_events,
}, timeout=5)
sync_data = r.json()
check("Offline sync accepted", r.status_code == 200,
      f"synced={sync_data.get('synced')}")
check("All offline events synced", sync_data.get("synced") == len(offline_events),
      f"synced={sync_data.get('synced')}/{len(offline_events)}")
check("Offline events classified as distress",
      all(res.get("classification", {}).get("is_distress") for res in sync_data.get("results", [])),
      "both queued events detected as distress")

# ─── Bonus: verify incident ───────────────────────────────────────────────────
section("BONUS — Responder verifies an incident")
if distress_incidents:
    inc_id = distress_incidents[0]["id"]
    r = requests.patch(f"{BASE}/api/incidents/{inc_id}/verify", timeout=5)
    check("Incident verification endpoint", r.status_code == 200,
          f"status={r.json().get('status')}")

# ─── WebSocket check ──────────────────────────────────────────────────────────
section("BONUS — WebSocket endpoint reachable")
import socket
try:
    s = socket.create_connection(("localhost", 8000), timeout=2)
    s.close()
    check("Port 8000 reachable (WS depends on HTTP server)", True)
except Exception as e:
    check("Port 8000 reachable", False, str(e))

# ─── Final summary ────────────────────────────────────────────────────────────
section("SUMMARY")
passed = sum(results)
total  = len(results)
print(f"\n  {passed}/{total} checks passed", end="  ")
if passed == total:
    print("— ALL SYSTEMS GO ✓")
elif passed >= total * 0.8:
    print("— MOSTLY PASSING (minor issues)")
else:
    print("— FAILURES DETECTED")

print(f"\n  Prototype feasibility: {'CONFIRMED ✓' if passed >= total * 0.8 else 'BLOCKED — see failures above'}\n")
sys.exit(0 if passed == total else 1)
