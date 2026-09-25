"""
CrisisMesh Audio Intelligence Module
Keyword spotting + confidence scoring without heavy ML deps.
In production: replace with a fine-tuned audio model (YAMNet / Wav2Vec2).
"""
import re
import math
from typing import Optional

DISTRESS_KEYWORDS = {
    "critical": ["help", "save me", "trapped", "can't breathe", "dying", "i'm dying", "please help"],
    "high":     ["stuck", "emergency", "rescue", "hurt", "injured", "fire", "can't move"],
    "medium":   ["please", "someone", "anyone", "hear me", "in here", "over here"],
}

KNOCK_PATTERNS = ["knock", "knocking", "banging", "tapping"]
CRY_PATTERNS   = ["crying", "sobbing", "screaming", "shouting", "yelling"]


def _keyword_score(text: str) -> tuple[float, str]:
    """Return (raw_score 0-1, detected_tier)."""
    lower = text.lower()
    for tier, words in DISTRESS_KEYWORDS.items():
        for w in words:
            if w in lower:
                base = {"critical": 0.90, "high": 0.72, "medium": 0.50}[tier]
                # bonus for all-caps urgency
                if text.isupper():
                    base = min(1.0, base + 0.06)
                # bonus for repeated exclamation
                bonus = min(0.05, text.count("!") * 0.01)
                return round(base + bonus, 3), tier
    return 0.0, "none"


def _event_type_from_text(text: str, hint: Optional[str] = None) -> str:
    if hint:
        return hint
    lower = text.lower()
    for p in KNOCK_PATTERNS:
        if p in lower:
            return "knocking"
    for p in CRY_PATTERNS:
        if p in lower:
            return "crying"
    if any(w in lower for w in DISTRESS_KEYWORDS["critical"]):
        return "verbal_distress"
    if any(w in lower for w in DISTRESS_KEYWORDS["high"]):
        return "verbal_distress"
    return "ambient_noise"


def _priority_from_confidence(conf: float) -> str:
    if conf >= 0.85:
        return "CRITICAL"
    if conf >= 0.65:
        return "HIGH"
    if conf >= 0.40:
        return "MEDIUM"
    return "LOW"


def classify(transcript: str, event_type_hint: Optional[str] = None) -> dict:
    """
    Classify a distress transcript.

    Returns:
        {
            event_type: str,
            confidence: float,   # 0.0 – 1.0
            priority: str,       # LOW / MEDIUM / HIGH / CRITICAL
            keywords_found: list,
            is_distress: bool,
        }
    """
    score, tier = _keyword_score(transcript)
    evt_type = _event_type_from_text(transcript, event_type_hint)

    # knocking always gets a base score if nothing else matched
    if evt_type == "knocking" and score == 0.0:
        score = 0.55

    # collect matched keywords for explainability
    lower = transcript.lower()
    found = []
    for words in DISTRESS_KEYWORDS.values():
        for w in words:
            if w in lower and w not in found:
                found.append(w)

    return {
        "event_type":    evt_type,
        "confidence":    score,
        "priority":      _priority_from_confidence(score),
        "keywords_found": found,
        "is_distress":   score >= 0.40,
        "tier":          tier,
    }
