"""
CrisisMesh Signal Fusion Engine
Groups nearby, recent events into one ranked incident.
"""
import math
from datetime import datetime, timedelta
from typing import Optional


PROXIMITY_METERS   = 250   # events within this radius are candidates to cluster
TIME_WINDOW_SECS   = 600   # 10-minute window
MIN_CONFIDENCE     = 0.40  # ignore noise-only signals


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in meters between two GPS coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi  = math.radians(lat2 - lat1)
    dlam  = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def combined_confidence(confidences: list[float]) -> float:
    """
    Bayesian-style combination:  1 - Π(1 - cᵢ)
    Multiple weak signals compound into a stronger alert.
    """
    result = 1.0
    for c in confidences:
        result *= (1.0 - c)
    return round(1.0 - result, 3)


def priority_from_confidence(conf: float) -> str:
    if conf >= 0.85:
        return "CRITICAL"
    if conf >= 0.65:
        return "HIGH"
    if conf >= 0.40:
        return "MEDIUM"
    return "LOW"


def find_cluster(new_event: dict, existing_events: list[dict]) -> list[dict]:
    """
    Return events that are spatially and temporally close to new_event.
    new_event and each item in existing_events must have: lat, lon, timestamp (ISO str), confidence.
    """
    if new_event["confidence"] < MIN_CONFIDENCE:
        return []

    new_ts = datetime.fromisoformat(new_event["timestamp"])
    cluster = []
    for ev in existing_events:
        if ev["confidence"] < MIN_CONFIDENCE:
            continue
        ev_ts = datetime.fromisoformat(ev["timestamp"])
        if abs((new_ts - ev_ts).total_seconds()) > TIME_WINDOW_SECS:
            continue
        dist = haversine(new_event["lat"], new_event["lon"], ev["lat"], ev["lon"])
        if dist <= PROXIMITY_METERS:
            cluster.append(ev)
    return cluster


def sector_label(lat: float, lon: float) -> str:
    """Very simple grid sector – good enough for demo."""
    row = chr(ord("A") + int((lat % 1) * 10) % 26)
    col = int((lon % 1) * 100) % 99 + 1
    return f"{row}-{col:02d}"
