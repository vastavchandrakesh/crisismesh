"""
CrisisMesh — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""
import uuid
import json
import asyncio
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import get_conn, init_db
from ai_classifier import classify
from fusion import find_cluster, combined_confidence, priority_from_confidence, sector_label

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="CrisisMesh API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

# ─── Demo state ───────────────────────────────────────────────────────────────
_demo_zone_id: Optional[str] = None
_demo_device_counter = 0

DEMO_EVENTS = {
    "help":     ("HELP! HELP! I am trapped under rubble!",    "verbal_distress", 0.0001, 0.0002),
    "trapped":  ("I am trapped, please send rescue immediately", "verbal_distress", 0.0002, 0.0001),
    "knocking": ("knocking knocking knocking",                "knocking",        0.0001, 0.0003),
    "noise":    ("background noise wind",                     "ambient_noise",   0.5000, 0.5000),
    "medical":  ("someone please hear me, I can't move",      "verbal_distress", 0.0002, 0.0002),
    "crying":   ("crying sobbing please someone help",        "crying",          0.0001, 0.0001),
}

DEMO_USERS = {
    "responder": {"password": "demo123", "role": "RESPONDER"},
    "admin":     {"password": "admin123", "role": "ADMIN"},
}


# ─── WebSocket broadcast ───────────────────────────────────────────────────────
class _WSManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, payload: dict):
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = _WSManager()


@app.websocket("/ws/dashboard")
async def ws_dashboard(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ─── Request / Response models ─────────────────────────────────────────────────
class ZoneCreate(BaseModel):
    name: str
    lat: float
    lon: float
    radius_m: float = 5000.0


class ConsentRequest(BaseModel):
    device_id: str
    zone_id: str


class AudioEventRequest(BaseModel):
    device_id: str
    zone_id: str
    transcript: str
    event_type_hint: Optional[str] = None
    lat: float
    lon: float
    offline_flag: bool = False


class OfflineSyncRequest(BaseModel):
    device_id: str
    events: List[AudioEventRequest]


class LoginRequest(BaseModel):
    username: str
    password: str


class DemoEventRequest(BaseModel):
    event_type: str
    offline: bool = False


# ─── Helpers ───────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.utcnow().isoformat()


def _row_to_dict(row) -> dict:
    return dict(row) if row else {}


def _freshness(updated_at: str) -> dict:
    try:
        dt = datetime.fromisoformat(updated_at)
        age_s = (datetime.utcnow() - dt).total_seconds()
        if age_s < 120:    label, score = "Fresh",  1.00
        elif age_s < 600:  label, score = "Recent", 0.75
        elif age_s < 1800: label, score = "Aging",  0.40
        else:              label, score = "Stale",  0.10
        return {"label": label, "score": round(score, 2), "age_seconds": int(age_s)}
    except Exception:
        return {"label": "Unknown", "score": 0, "age_seconds": 0}


def _audit(conn, action: str, actor: str = "system",
           entity_type: str = "", entity_id: str = "", detail: str = ""):
    conn.execute(
        "INSERT INTO audit_logs VALUES (?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), action, actor, entity_type, entity_id, detail, _now()),
    )


def _get_or_create_demo_zone(conn) -> str:
    global _demo_zone_id
    if _demo_zone_id:
        row = conn.execute("SELECT id FROM zones WHERE id=? AND active=1", (_demo_zone_id,)).fetchone()
        if row:
            return _demo_zone_id
    row = conn.execute("SELECT id FROM zones WHERE active=1 LIMIT 1").fetchone()
    if row:
        _demo_zone_id = row["id"]
        return _demo_zone_id
    zone_id = str(uuid.uuid4())
    conn.execute("INSERT INTO zones VALUES (?,?,?,?,?,1,?)",
                 (zone_id, "Demo Zone Alpha", 12.9716, 77.5946, 3000, _now()))
    _audit(conn, "ZONE_CREATED", "system", "zone", zone_id, "Demo Zone Alpha")
    conn.commit()
    _demo_zone_id = zone_id
    return zone_id


# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = DEMO_USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(401, "Invalid credentials")
    conn = get_conn()
    try:
        _audit(conn, "LOGIN", body.username)
        conn.commit()
    finally:
        conn.close()
    return {"username": body.username, "role": user["role"], "token": "demo-token"}


# ─── Zone endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/zones", status_code=201)
def create_zone(body: ZoneCreate):
    zone_id = str(uuid.uuid4())
    conn = get_conn()
    try:
        conn.execute("INSERT INTO zones VALUES (?,?,?,?,?,1,?)",
                     (zone_id, body.name, body.lat, body.lon, body.radius_m, _now()))
        _audit(conn, "ZONE_CREATED", "responder", "zone", zone_id, body.name)
        conn.commit()
    finally:
        conn.close()
    return {"id": zone_id, **body.model_dump(), "active": True}


@app.get("/api/zones")
def list_zones():
    conn = get_conn()
    try:
        rows = conn.execute("SELECT * FROM zones WHERE active=1").fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


@app.get("/api/devices")
def list_devices():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT device_id, zone_id, consented_at FROM device_consents WHERE active=1 ORDER BY consented_at DESC LIMIT 50"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ─── Consent endpoints ──────────────────────────────────────────────────────────
@app.post("/api/devices/consent", status_code=201)
def grant_consent(body: ConsentRequest):
    conn = get_conn()
    try:
        zone = conn.execute("SELECT id FROM zones WHERE id=? AND active=1", (body.zone_id,)).fetchone()
        if not zone:
            raise HTTPException(404, "Zone not found or inactive")
        conn.execute("INSERT OR REPLACE INTO device_consents VALUES (?,?,?,1)",
                     (body.device_id, body.zone_id, _now()))
        _audit(conn, "CONSENT_GRANTED", body.device_id, "device", body.device_id, body.zone_id)
        conn.commit()
    finally:
        conn.close()
    return {"device_id": body.device_id, "zone_id": body.zone_id, "consented": True}


@app.delete("/api/devices/{device_id}/consent")
def revoke_consent(device_id: str):
    conn = get_conn()
    try:
        conn.execute("UPDATE device_consents SET active=0 WHERE device_id=?", (device_id,))
        _audit(conn, "CONSENT_REVOKED", device_id, "device", device_id)
        conn.commit()
    finally:
        conn.close()
    return {"device_id": device_id, "consented": False}


# ─── Core: submit audio event ──────────────────────────────────────────────────
async def _process_event(evt_req: AudioEventRequest, background: BackgroundTasks) -> dict:
    conn = get_conn()
    try:
        return await _process_event_inner(evt_req, background, conn)
    finally:
        conn.close()


async def _process_event_inner(evt_req: AudioEventRequest, background: BackgroundTasks, conn) -> dict:
    # 1. Verify consent
    consent = conn.execute(
        "SELECT * FROM device_consents WHERE device_id=? AND zone_id=? AND active=1",
        (evt_req.device_id, evt_req.zone_id),
    ).fetchone()
    if not consent:
        raise HTTPException(403, "Device has not consented for this zone")

    # 2. AI classification
    result = classify(evt_req.transcript, evt_req.event_type_hint)

    # 3. Persist event
    event_id = str(uuid.uuid4())
    ts = _now()
    conn.execute(
        """INSERT INTO audio_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            event_id, evt_req.device_id, evt_req.zone_id,
            evt_req.transcript, result["event_type"],
            result["confidence"], result["priority"],
            json.dumps(result["keywords_found"]),
            evt_req.lat, evt_req.lon, ts,
            1 if result["is_distress"] else 0,
            1 if evt_req.offline_flag else 0,
            1,
        ),
    )
    _audit(conn, "EVENT_CREATED", evt_req.device_id, "audio_event", event_id,
           f"{result['event_type']}|conf={result['confidence']:.2f}")
    conn.commit()

    incident_id = None

    if result["is_distress"]:
        # 4. Find nearby events for fusion
        existing_rows = conn.execute(
            """SELECT id, lat, lon, timestamp, confidence FROM audio_events
               WHERE zone_id=? AND is_distress=1 AND id!=?
               ORDER BY timestamp DESC LIMIT 50""",
            (evt_req.zone_id, event_id),
        ).fetchall()
        existing = [_row_to_dict(r) for r in existing_rows]

        new_ev = {
            "id": event_id, "lat": evt_req.lat, "lon": evt_req.lon,
            "timestamp": ts, "confidence": result["confidence"],
        }
        cluster = find_cluster(new_ev, existing)

        if cluster:
            cluster_ids = tuple(c["id"] for c in cluster)
            ph = ",".join("?" * len(cluster_ids))
            inc_row = conn.execute(
                f"SELECT incident_id FROM incident_events WHERE event_id IN ({ph}) LIMIT 1",
                cluster_ids,
            ).fetchone()

            if inc_row:
                incident_id = inc_row["incident_id"]
                all_confs = [c["confidence"] for c in cluster] + [result["confidence"]]
                new_conf = combined_confidence(all_confs)
                new_pri = priority_from_confidence(new_conf)
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM incident_events WHERE incident_id=?", (incident_id,)
                ).fetchone()[0] + 1
                conn.execute(
                    """UPDATE incidents SET confidence=?, priority=?, event_count=?, updated_at=?
                       WHERE id=?""",
                    (new_conf, new_pri, cnt, ts, incident_id),
                )
                _audit(conn, "INCIDENT_UPDATED", evt_req.device_id, "incident", incident_id,
                       f"conf={new_conf:.2f}|events={cnt}")
            else:
                incident_id = None

        if not incident_id:
            incident_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    incident_id, evt_req.zone_id,
                    sector_label(evt_req.lat, evt_req.lon),
                    "NEEDS_VERIFICATION",
                    result["confidence"], result["priority"],
                    1, evt_req.lat, evt_req.lon, ts, ts,
                ),
            )
            _audit(conn, "INCIDENT_CREATED", evt_req.device_id, "incident", incident_id,
                   f"priority={result['priority']}")

        conn.execute("INSERT OR IGNORE INTO incident_events VALUES (?,?)", (incident_id, event_id))
        conn.commit()

    payload = {
        "event_id":    event_id,
        "incident_id": incident_id,
        "classification": result,
        "timestamp":   ts,
    }

    background.add_task(ws_manager.broadcast, {"type": "event", **payload})
    if incident_id:
        background.add_task(ws_manager.broadcast, {
            "type": "incident_update",
            "incident_id": incident_id,
        })

    return payload


@app.post("/api/events", status_code=201)
async def submit_event(body: AudioEventRequest, background: BackgroundTasks):
    return await _process_event(body, background)


# ─── Offline sync ───────────────────────────────────────────────────────────────
@app.post("/api/offline/sync")
async def sync_offline(body: OfflineSyncRequest, background: BackgroundTasks):
    results = []
    for ev in body.events:
        try:
            r = await _process_event(ev, background)
            results.append({"status": "ok", **r})
        except HTTPException as e:
            results.append({"status": "error", "detail": e.detail})
    synced = len([r for r in results if r["status"] == "ok"])
    conn = get_conn()
    try:
        _audit(conn, "SYNC_COMPLETED", body.device_id, "offline_sync", "",
               f"synced={synced}/{len(results)}")
        conn.commit()
    finally:
        conn.close()
    return {"synced": synced, "results": results}


# ─── Incidents ──────────────────────────────────────────────────────────────────
@app.get("/api/incidents")
def list_incidents(zone_id: Optional[str] = None):
    conn = get_conn()
    try:
        if zone_id:
            rows = conn.execute(
                "SELECT * FROM incidents WHERE zone_id=? ORDER BY confidence DESC", (zone_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM incidents ORDER BY confidence DESC").fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["freshness"] = _freshness(d.get("updated_at") or d.get("created_at", ""))
            result.append(d)
        return result
    finally:
        conn.close()


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    conn = get_conn()
    try:
        inc = conn.execute("SELECT * FROM incidents WHERE id=?", (incident_id,)).fetchone()
        if not inc:
            raise HTTPException(404, "Incident not found")
        evs = conn.execute(
            """SELECT ae.* FROM audio_events ae
               JOIN incident_events ie ON ae.id=ie.event_id
               WHERE ie.incident_id=?""",
            (incident_id,),
        ).fetchall()
        d = _row_to_dict(inc)
        d["freshness"] = _freshness(d.get("updated_at") or d.get("created_at", ""))
        return {**d, "events": [_row_to_dict(e) for e in evs]}
    finally:
        conn.close()


@app.patch("/api/incidents/{incident_id}/verify")
def verify_incident(incident_id: str):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE incidents SET status='VERIFIED', updated_at=? WHERE id=?",
            (_now(), incident_id),
        )
        _audit(conn, "INCIDENT_VERIFIED", "responder", "incident", incident_id)
        conn.commit()
    finally:
        conn.close()
    return {"incident_id": incident_id, "status": "VERIFIED"}


@app.patch("/api/incidents/{incident_id}/resolve")
def resolve_incident(incident_id: str):
    conn = get_conn()
    try:
        conn.execute(
            "UPDATE incidents SET status='RESOLVED', updated_at=? WHERE id=?",
            (_now(), incident_id),
        )
        _audit(conn, "INCIDENT_RESOLVED", "responder", "incident", incident_id)
        conn.commit()
    finally:
        conn.close()
    return {"incident_id": incident_id, "status": "RESOLVED"}


# ─── Demo endpoints ─────────────────────────────────────────────────────────────
@app.post("/api/demo/generate-event", status_code=201)
async def demo_generate_event(body: DemoEventRequest, background: BackgroundTasks):
    global _demo_device_counter
    key = body.event_type.lower()
    if key not in DEMO_EVENTS:
        raise HTTPException(400, f"Unknown event_type '{key}'. Valid: {list(DEMO_EVENTS)}")

    transcript, evt_hint, dlat, dlon = DEMO_EVENTS[key]
    _demo_device_counter += 1
    device_id = f"demo-{key[:3]}-{_demo_device_counter:02d}"

    conn = get_conn()
    try:
        zone_id = _get_or_create_demo_zone(conn)
        conn.execute("INSERT OR REPLACE INTO device_consents VALUES (?,?,?,1)",
                     (device_id, zone_id, _now()))
        _audit(conn, "CONSENT_GRANTED", device_id, "device", device_id, zone_id)
        conn.commit()
    finally:
        conn.close()

    req = AudioEventRequest(
        device_id=device_id,
        zone_id=zone_id,
        transcript=transcript,
        event_type_hint=evt_hint,
        lat=12.9716 + dlat,
        lon=77.5946 + dlon,
        offline_flag=body.offline,
    )
    return await _process_event(req, background)


@app.post("/api/demo/scenario", status_code=201)
async def demo_scenario(background: BackgroundTasks):
    """Building collapse scenario: HELP + TRAPPED + KNOCKING + NOISE + MEDICAL."""
    results = []
    for key in ["help", "trapped", "knocking", "noise", "medical"]:
        r = await demo_generate_event(DemoEventRequest(event_type=key), background)
        results.append(r)
        await asyncio.sleep(0.15)
    conn = get_conn()
    try:
        _audit(conn, "DEMO_SCENARIO_RUN", "demo", "", "", "building_collapse")
        conn.commit()
    finally:
        conn.close()
    return {"generated": len(results), "results": results}


@app.post("/api/demo/reset")
def demo_reset():
    global _demo_zone_id, _demo_device_counter
    conn = get_conn()
    try:
        conn.executescript("""
            DELETE FROM incident_events;
            DELETE FROM incidents;
            DELETE FROM audio_events;
            DELETE FROM device_consents;
            DELETE FROM zones;
            DELETE FROM offline_queue;
            DELETE FROM audit_logs;
        """)
        conn.commit()
    finally:
        conn.close()
    _demo_zone_id = None
    _demo_device_counter = 0
    return {"status": "reset", "message": "All demo data cleared"}


# ─── Audit log ──────────────────────────────────────────────────────────────────
@app.get("/api/audit")
def list_audit():
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 100"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ─── Health ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "service": "CrisisMesh", "time": _now()}
