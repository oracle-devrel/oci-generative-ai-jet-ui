from __future__ import annotations


def apply_mastery_band(score: float) -> str:
    if score < 25:
        return "Fragile"
    if score < 70:
        return "Developing"
    if score < 85:
        return "Solid"
    return "Strong"


def clamp_score(score: float) -> float:
    return max(0.0, min(100.0, round(score, 2)))


def trend_from_delta(delta: float) -> str:
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


def score_concept_update(
    *,
    score_before: float,
    explanation_length: int,
    user_turn_count: int,
    hints_used_count: int,
    confusion_detected: bool,
) -> tuple[float, float]:
    delta = 0.0

    if user_turn_count > 0:
        delta += 8
    if explanation_length >= 120:
        delta += 8
    elif explanation_length >= 60:
        delta += 6
    elif explanation_length >= 20:
        delta += 3

    if user_turn_count > 1:
        delta += 4

    if confusion_detected:
        delta -= 3

    if hints_used_count > 0:
        delta -= min(4, hints_used_count * 2)

    score_after = clamp_score(score_before + delta)
    return round(delta, 2), score_after
