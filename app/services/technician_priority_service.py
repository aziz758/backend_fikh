from __future__ import annotations

from app.config import settings


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_weights(distance_w: float, rating_w: float, acceptance_w: float, completion_w: float):
    weights = [max(0.0, distance_w), max(0.0, rating_w), max(0.0, acceptance_w), max(0.0, completion_w)]
    total = sum(weights)
    if total <= 0:
        return (0.5, 0.25, 0.15, 0.1)
    return tuple(weight / total for weight in weights)


def get_priority_weights() -> tuple[float, float, float, float]:
    return _normalize_weights(
        _to_float(settings.TECHNICIAN_PRIORITY_DISTANCE_WEIGHT, 0.5),
        _to_float(settings.TECHNICIAN_PRIORITY_RATING_WEIGHT, 0.25),
        _to_float(settings.TECHNICIAN_PRIORITY_ACCEPTANCE_WEIGHT, 0.15),
        _to_float(settings.TECHNICIAN_PRIORITY_COMPLETION_WEIGHT, 0.1),
    )


def _distance_score(distance_km: float | None, max_distance_km: float | None) -> float | None:
    if distance_km is None or max_distance_km is None:
        return None
    max_distance = _to_float(max_distance_km, 0.0)
    if max_distance <= 0:
        return None
    return _clamp01(1.0 - (_to_float(distance_km, 0.0) / max_distance))


def compute_technician_priority_score(
    *,
    distance_km: float | None,
    max_distance_km: float | None,
    avg_rating: float | None,
    acceptance_rate: float | None,
    completion_rate: float | None,
) -> float:
    distance_weight, rating_weight, acceptance_weight, completion_weight = get_priority_weights()

    rating_score = _clamp01(_to_float(avg_rating, 0.0) / 5.0)
    acceptance_score = _clamp01(_to_float(acceptance_rate, 0.0))
    completion_score = _clamp01(_to_float(completion_rate, 0.0))

    distance_score = _distance_score(distance_km, max_distance_km)
    if distance_score is None:
        distance_weight = 0.0

    total_weight = distance_weight + rating_weight + acceptance_weight + completion_weight
    if total_weight <= 0:
        return 0.0

    score_sum = (
        (distance_weight * (distance_score if distance_score is not None else 0.0))
        + (rating_weight * rating_score)
        + (acceptance_weight * acceptance_score)
        + (completion_weight * completion_score)
    )
    return score_sum / total_weight
