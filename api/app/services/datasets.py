from __future__ import annotations

from typing import Any, Dict, Optional

"""
distributions_json structure:
{
  "stature": [
    {
      "region": "NA",        # or "all"
      "sex": "M",            # "M" | "F" | "all"
      "age": "18-25",        # age band label or "all"
      "percentiles": {        # representative values (units documented by dataset)
        "p5": 165.0,
        "p50": 177.0,
        "p95": 190.0
      }
    },
    ...
  ],
  "weight": [ ... ]
}

Percentile interpolation:
- For requested percentile p (0-100), we linearly interpolate between
  (5 -> p5) and (50 -> p50) when p <= 50; between (50 -> p50) and (95 -> p95) when p > 50.
- Values below 5 clamp to p5; above 95 clamp to p95.
"""


def _choose_segment(
    entries: list[dict[str, Any]],
    region: Optional[str],
    sex: Optional[str],
    age: Optional[str],
) -> Optional[dict[str, Any]]:
    # Score-based best match. Exact match scores highest; 'all' acts as wildcard.
    best = None
    best_score = -1
    for e in entries:
        score = 0
        if region and e.get("region", "all") == region:
            score += 2
        elif e.get("region", "all") == "all":
            score += 1
        if sex and e.get("sex", "all") == sex:
            score += 2
        elif e.get("sex", "all") == "all":
            score += 1
        if age and e.get("age", "all") == age:
            score += 2
        elif e.get("age", "all") == "all":
            score += 1
        if score > best_score:
            best = e
            best_score = score
    return best


def interpolate_percentile(p5: float, p50: float, p95: float, p: float) -> float:
    if p <= 5:
        return p5
    if p >= 95:
        return p95
    if p <= 50:
        # interpolate between (5, p5) and (50, p50)
        t = (p - 5.0) / (50.0 - 5.0)
        return p5 + t * (p50 - p5)
    else:
        t = (p - 50.0) / (95.0 - 50.0)
        return p50 + t * (p95 - p50)


def query_percentile(
    distributions: Dict[str, list[dict]],
    metric: str,
    percentile: float,
    *,
    region: Optional[str] = None,
    sex: Optional[str] = None,
    age: Optional[str] = None,
) -> float:
    entries = distributions.get(metric) or []
    if not entries:
        raise KeyError(f"Metric not found: {metric}")
    seg = _choose_segment(entries, region, sex, age)
    if not seg:
        raise KeyError("No matching segment")
    ps = seg.get("percentiles") or {}
    p5 = float(ps.get("p5"))
    p50 = float(ps.get("p50"))
    p95 = float(ps.get("p95"))
    return interpolate_percentile(p5, p50, p95, float(percentile))
