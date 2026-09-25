# CrisisMesh

**AI-Powered Audio Intelligence for Faster Disaster Victim Detection**

---

## The Problem

During building collapses, earthquakes, and mass casualty events, victims may be physically close to rescuers but impossible to locate. The problem is not communication — it is signal noise. Responders receive dozens of fragmented, duplicated, low-confidence reports and cannot manually inspect every possible audio source in time.

## The Solution

CrisisMesh is a software-first emergency intelligence layer. Phones in an affected area (with explicit user consent) capture short audio clips and send them to a backend that:

1. Classifies each clip for distress signals (screaming, knocking, "help", "trapped")
2. Assigns a confidence score to each signal
3. Fuses nearby signals from multiple devices into a single clustered incident
4. Presents responders with a prioritised, deduplicated incident list on a live dashboard

The result: 12 raw signals from 4 devices become **1 actionable incident** with an explainable confidence score — not 12 separate alerts.

CrisisMesh **supports** responders. It does not make rescue decisions automatically.

---

## Architecture

```
Affected Device (phone)
        │  explicit consent + audio transcript
        ▼
  POST /api/events
        │
        ▼
  AI Classifier ──► keyword spotting, confidence scoring
        │
        ▼
  Fusion Engine ──► haversine clustering, corroboration
        │
        ▼
  SQLite Database
        │
        ▼
  WebSocket broadcast ──► Responder Dashboard (live map + incident list)
```

### Offline path

```
Device (no connectivity)
        │  events queued locally in browser
        ▼
  Connection restored
        │
        ▼
  POST /api/offline/sync  (offline_flag=true on each event)
        │
        ▼
  Normal pipeline → Dashboard updates
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x + FastAPI + Uvicorn |
| Database | SQLite (stdlib `sqlite3`, WAL mode) |
| AI / classifier | Keyword spotting + confidence scoring (no heavy ML deps) |
| Fusion | Haversine distance clustering |
| Real-time | WebSocket (FastAPI native) |
| Frontend | Vanilla HTML + CSS + JavaScript (no framework, no build step) |
| Map | Leaflet 1.9.4 (bundled locally — works offline) |
| Map tiles | OpenStreetMap (requires internet; cached after first load) |

---

## Setup

### Prerequisites

- Python 3.10+
- pip

### Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Backend runs at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

### Open the dashboard

Open `dashboard/index.html` directly in a browser. No build step required.

> Leaflet is bundled locally in `dashboard/leaflet/` so the map loads without internet.  
> Map tiles (the actual street imagery) still require an internet connection.

---

## Demo Credentials

| Username | Password | Role |
|---|---|---|
| `responder` | `demo123` | RESPONDER |
| `admin` | `admin123` | ADMIN |

These are hardcoded demo credentials. There is no production authentication system.

---

## 3-Minute Demo Walkthrough

1. Open `dashboard/index.html` → sign in as `responder / demo123`
2. Switch to the **Demo ⚡** tab
3. Click **START FULL SCENARIO** — 5 simulated devices fire alerts; 1 clustered incident appears on the map and sidebar
4. Click the incident card to expand evidence (HELP + TRAPPED + KNOCKING fused into one incident)
5. Click **✓ Verify** then **Resolve** to walk through the responder workflow
6. Click **SIMULATE CONNECTION LOSS** → generate 2 more events → watch them queue locally
7. Click **RESTORE & SYNC** → offline events appear on the dashboard tagged `[offline sync]`
8. Switch to the **Relay** tab → click **ANIMATE RELAY** to show the Bluetooth mesh relay chain
9. Switch to the **Audit** tab → show the complete consent + event + verification trail

### Simulator (alternative to the Demo tab)

If you prefer to drive events from the terminal:

```bash
cd simulator
python device_simulator.py
```

The simulator auto-creates a zone and runs the full building collapse scenario.  
You can also pass an existing zone ID:

```bash
python device_simulator.py --zone-id <uuid>
```

### Smoke test

```bash
cd ..
python smoke_test.py
```

Runs an end-to-end test of all 8 demo criteria against a running backend.

---

## Demo Scenario

**Incident: Building collapse, Sector A-12**

| Device | Signal | Confidence |
|---|---|---|
| demo-hel-01 | "HELP! HELP! I am trapped under rubble!" | ~0.96 |
| demo-tra-02 | "I am trapped, please send rescue immediately" | ~0.90 |
| demo-kno-03 | "knocking knocking knocking" | ~0.55 |
| demo-noi-04 | "background noise wind" | ~0.00 (not distress) |
| demo-med-05 | "someone please hear me, I can't move" | ~0.90 |

Expected result: **1 CRITICAL incident** fusing devices 01, 02, 03, 05. Device 04 does not contribute meaningfully (ambient noise, low confidence, far coordinates).

---

## API Overview

| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Demo login |
| GET | `/api/zones` | List active emergency zones |
| POST | `/api/zones` | Create a zone |
| GET | `/api/devices` | List consented devices |
| POST | `/api/devices/consent` | Grant device consent |
| DELETE | `/api/devices/{id}/consent` | Revoke consent |
| POST | `/api/events` | Submit audio event |
| POST | `/api/offline/sync` | Sync queued offline events |
| GET | `/api/incidents` | List all incidents (with freshness) |
| GET | `/api/incidents/{id}` | Get incident + evidence events |
| PATCH | `/api/incidents/{id}/verify` | Mark incident VERIFIED |
| PATCH | `/api/incidents/{id}/resolve` | Mark incident RESOLVED |
| POST | `/api/demo/generate-event` | Generate a single typed demo event |
| POST | `/api/demo/scenario` | Run full building collapse scenario |
| POST | `/api/demo/reset` | Clear all demo data |
| GET | `/api/audit` | Audit log (last 100 entries) |
| GET | `/health` | Health check |
| WS | `/ws/dashboard` | Live dashboard WebSocket |

Full OpenAPI spec: `http://localhost:8000/docs`

---

## Privacy Model

- **No silent activation.** Audio processing only begins after explicit user opt-in.
- **Pseudonymized device IDs.** Devices are identified as `demo-xxx-01` format — no real phone numbers or names.
- **Minimum metadata.** Only transcript text, event type, confidence, and approximate coordinates are stored.
- **Local storage only.** All data stays in `backend/crisismesh.db` on the local machine. Nothing is sent to any cloud service.
- **Consent is revocable.** `DELETE /api/devices/{id}/consent` removes a device from all future processing.
- **Stop monitoring.** The dashboard's Reset Demo button clears all stored data.

Every consent grant, event, and incident action is written to the audit log.

---

## Offline Behavior

When connectivity is lost (click **SIMULATE CONNECTION LOSS** in the Demo tab):

- New demo events are queued in browser memory
- The UI shows an `OFFLINE MODE` banner with a queue count
- No events are silently dropped or marked as delivered

When connectivity is restored (click **RESTORE & SYNC**):

- Queued events are sent to `/api/offline/sync` with `offline_flag: true`
- They process through the normal classification and fusion pipeline
- Evidence cards show an `[offline sync]` tag so responders know the event was delayed

---

## Confidence Score

Each event gets a score from the keyword classifier:

| Tier | Keywords | Base score |
|---|---|---|
| Critical | help, save me, trapped, can't breathe, dying | 0.90 |
| High | stuck, emergency, rescue, hurt, injured, fire | 0.72 |
| Medium | please, someone, hear me, in here | 0.50 |
| Knocking | knocking, banging, tapping (no keyword match) | 0.55 |
| None | no match | 0.00 |

All-caps urgency adds +0.06. Each `!` adds +0.01 (capped at +0.05).

When multiple events cluster into one incident, confidence is combined using a corroboration formula that rewards signal agreement without simply averaging.

Incident priority thresholds: CRITICAL ≥ 0.85 · HIGH ≥ 0.65 · MEDIUM ≥ 0.40 · LOW < 0.40

---

## Freshness

Incidents carry a freshness label that decays over time:

| Age | Label | Score |
|---|---|---|
| < 2 minutes | Fresh | 1.00 |
| 2 – 10 minutes | Recent | 0.75 |
| 10 – 30 minutes | Aging | 0.40 |
| > 30 minutes | Stale | 0.10 |

The dashboard refreshes incident freshness every 30 seconds automatically.

---

## Known Limitations

- **No real audio capture.** The classifier works on transcript text only. Actual audio-to-text (e.g. Whisper) would need to be added as a pre-processing step before the classifier.
- **No real Bluetooth mesh.** The Relay tab is a visual software simulation. Real BLE/Wi-Fi Direct mesh would require a native mobile app.
- **No real authentication.** Credentials are hardcoded. A production system would need JWT, role-based access control, and MFA.
- **SQLite single-writer.** Fine for a demo; a production system would use PostgreSQL.
- **Map tiles require internet.** Leaflet itself is bundled locally, but OpenStreetMap tile imagery needs a network connection. A local tile server (e.g. MBTiles) would be needed for fully offline operation.
- **No freshness decay action.** Stale incidents are labelled but not automatically escalated or removed. A background task could auto-mark them.
- **Classifier is keyword-only.** It cannot handle paraphrasing, non-English text, or audio-only distress signals (e.g. crying without words). A real deployment would need a fine-tuned audio model (YAMNet, Wav2Vec2).

---

## Future Extensions

- Replace keyword classifier with an on-device audio model (YAMNet or Whisper)
- Real Bluetooth LE / Wi-Fi Direct mesh relay via native Android/iOS app
- JWT authentication with role-based access (RESPONDER, COMMAND, ADMIN)
- PostgreSQL + Redis for multi-instance deployment
- Push notifications to responder devices on new CRITICAL incidents
- Geofenced zone activation (auto-activate emergency mode when device enters zone)
- Multi-language keyword detection
- Incident assignment and team coordination
- Export audit log to CSV for post-incident review

---

## Project Structure

```
crisismesh/
├── backend/
│   ├── main.py          — FastAPI app, all REST + WebSocket endpoints
│   ├── database.py      — SQLite schema + connection factory
│   ├── ai_classifier.py — Keyword classifier + confidence scoring
│   ├── fusion.py        — Haversine clustering + corroboration engine
│   ├── requirements.txt
│   └── crisismesh.db    — SQLite database (auto-created on first run)
├── dashboard/
│   ├── index.html       — Single-file frontend (map, incidents, demo panel)
│   └── leaflet/         — Leaflet 1.9.4 bundled locally
├── simulator/
│   └── device_simulator.py — Terminal-based demo traffic generator
├── smoke_test.py        — End-to-end test of all demo criteria
├── skill.md             — Original build specification
└── README.md
```

---

*CrisisMesh is a 24-hour hackathon prototype. It is not validated for real emergency deployment.*
