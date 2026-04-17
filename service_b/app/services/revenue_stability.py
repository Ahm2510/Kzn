"""
Revenue Stability Index (V1 — Additive)
 
Computes a deterministic, normalized 0–100 stability score for a revenue dataset.
This module is fully standalone — it does not modify any existing computation logic.
 
Score bands:
    80–100  Very Stable
    60–79   Moderately Stable
    40–59   Unstable
    0–39    Highly Unstable
 
Components (deterministic):
    1. CV Score           50% weight   (0–50 pts)
    2. Spike Penalty      25% weight   (0–25 pts)
    3. Baseline Drift     25% weight   (0–25 pts, neutral 12.5 if no baseline)
"""
from __future__ import annotations
 
from typing import List, Optional
 
import pandas as pd
from pydantic import BaseModel
 
 
class RevenueStabilityResult(BaseModel):
    """Structured result for the Revenue Stability Index."""
 
    score: float                     # 0–100, rounded to 1 decimal place
    label: str                       # "Very Stable" / "Moderately Stable" / "Unstable" / "Highly Unstable"
    confidence: str                  # "high" / "medium" / "low"
    explanation: str                 # One human-readable paragraph
    contributing_factors: List[str]  # Bullet-ready factor descriptions
    warning: Optional[str] = None    # Set when n < 20 or data is sparse
    coefficient_of_variation: float  # Raw CV used in computation
    spike_ratio: float               # Fraction of revenue concentrated in top 5% of transactions
    has_baseline_comparison: bool    # Whether baseline was incorporated
 
 
# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────
 
def _cv_to_score(cv: float) -> float:
    """
    Piecewise linear map: coefficient of variation → sub-score on 0–100 scale.
 
    Calibrated so that:
        CV = 0.0  → 100   (perfectly stable)
        CV = 0.3  →  80   (stable boundary)
        CV = 0.7  →  50   (unstable boundary)
        CV = 1.5  →  15   (highly volatile)
        CV ≥ 2.0  →   0   (critical)
    """
    if cv <= 0.0:
        return 100.0
    if cv <= 0.3:
        return 100.0 - (cv / 0.3) * 20.0            # 100 → 80
    if cv <= 0.7:
        return 80.0 - ((cv - 0.3) / 0.4) * 30.0     # 80  → 50
    if cv <= 1.5:
        return 50.0 - ((cv - 0.7) / 0.8) * 35.0     # 50  → 15
    return max(0.0, 15.0 - ((cv - 1.5) / 0.5) * 15.0)  # 15 → 0
 
 
def _label_from_score(score: float) -> str:
    if score >= 80.0:
        return "Very Stable"
    if score >= 60.0:
        return "Moderately Stable"
    if score >= 40.0:
        return "Unstable"
    return "Highly Unstable"
 
 
def _cv_interpretation(cv: float) -> str:
    if cv < 0.3:
        return "low volatility — consistent revenue"
    if cv < 0.7:
        return "moderate volatility"
    if cv < 1.0:
        return "high volatility"
    return "extreme volatility"
 
 
def _build_explanation(
    score: float,
    cv: float,
    spike_ratio: float,
    has_baseline: bool,
) -> str:
    label = _label_from_score(score)
 
    if cv < 0.3:
        cv_clause = "Revenue values are tightly distributed with low variation"
    elif cv < 0.7:
        cv_clause = "Revenue shows moderate variation across transactions"
    else:
        cv_clause = "Revenue varies substantially between transactions, reducing predictability"
 
    if spike_ratio < 0.25:
        spike_clause = "transaction values are broadly distributed without dominant spikes"
    elif spike_ratio < 0.50:
        spike_clause = "a moderate spike concentration exists in the top 5% of transactions"
    else:
        spike_clause = "the top 5% of transactions are driving a disproportionate share of revenue"
 
    baseline_note = (
        " Baseline period volatility was incorporated into the score."
        if has_baseline
        else ""
    )
 
    return (
        f"Revenue stability score is {score:.0f}/100 — {label.lower()}. "
        f"{cv_clause}, and {spike_clause}.{baseline_note}"
    )
 
 
# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────
 
def compute_revenue_stability_index(
    current_df: pd.DataFrame,
    revenue_column: str,
    baseline_df: Optional[pd.DataFrame] = None,
    baseline_revenue_column: Optional[str] = None,
) -> Optional[RevenueStabilityResult]:
    """
    Compute the Revenue Stability Index.
 
    Returns ``None`` if data is insufficient or any error occurs.
    This function never raises.
    """
    try:
        vals = pd.to_numeric(current_df[revenue_column], errors="coerce").dropna()
        n = len(vals)
 
        if n < 2 or vals.sum() == 0:
            return None
 
        mean_val = float(vals.mean())
        if mean_val == 0.0:
            return None
 
        # ── Component 1: CV Score (0–50 pts) ─────────────────────────────────
        cv = float(abs(vals.std() / mean_val))
        cv_score = _cv_to_score(cv) * 0.5           # Scale 0–100 → 0–50
 
        # ── Component 2: Spike Score (0–25 pts) ──────────────────────────────
        total_rev = float(vals.sum())
        top_n = max(1, int(n * 0.05))               # Top 5% of rows
        spike_sum = float(vals.sort_values(ascending=False).head(top_n).sum())
        spike_ratio = spike_sum / total_rev if total_rev > 0.0 else 0.0
 
        # Ideal: top-5% contributes proportionally (~5%). Severe: >50%.
        if spike_ratio <= 0.15:
            spike_score = 25.0
        elif spike_ratio <= 0.50:
            spike_score = 25.0 - ((spike_ratio - 0.15) / 0.35) * 10.0   # 25 → 15
        else:
            spike_score = max(0.0, 15.0 - ((spike_ratio - 0.50) / 0.50) * 15.0)  # 15 → 0
 
        # ── Component 3: Baseline Drift (0–25 pts) ───────────────────────────
        # Neutral = 12.5 when no baseline (no penalty for standalone analysis)
        has_baseline = False
        baseline_score = 12.5
        b_cv: Optional[float] = None
        baseline_cv_delta_pct: Optional[float] = None
 
        if (
            baseline_df is not None
            and not (isinstance(baseline_df, pd.DataFrame) and baseline_df.empty)
            and baseline_revenue_column is not None
        ):
            try:
                b_vals = pd.to_numeric(
                    baseline_df[baseline_revenue_column], errors="coerce"
                ).dropna()
                if len(b_vals) >= 2:
                    b_mean = float(b_vals.mean())
                    if b_mean > 0.0:
                        b_cv = float(abs(b_vals.std() / b_mean))
                        delta_ratio = abs(cv - b_cv) / max(b_cv, 0.01)
                        baseline_cv_delta_pct = delta_ratio * 100.0
                        # Tighter drift = more points (higher stability)
                        if delta_ratio < 0.10:
                            baseline_score = 25.0
                        elif delta_ratio < 0.30:
                            baseline_score = 20.0
                        elif delta_ratio < 0.50:
                            baseline_score = 12.0
                        elif delta_ratio < 1.00:
                            baseline_score = 6.0
                        else:
                            baseline_score = 0.0
                        has_baseline = True
            except Exception:
                pass  # Keep neutral baseline_score = 12.5
 
        # ── Final raw score ───────────────────────────────────────────────────
        raw = cv_score + spike_score + baseline_score
        score = round(min(100.0, max(0.0, raw)), 1)
 
        # ── Low-sample cap ────────────────────────────────────────────────────
        warning: Optional[str] = None
        if n < 10:
            score = min(score, 50.0)
            warning = (
                "Fewer than 10 revenue records available; "
                "stability index is directional only."
            )
        elif n < 20:
            score = min(score, 65.0)
            warning = "Low data volume; stability index may not be fully representative."
 
        # ── Confidence ────────────────────────────────────────────────────────
        if n >= 50 and cv < 1.0:
            confidence = "high"
        elif n >= 20:
            confidence = "medium"
        else:
            confidence = "low"
 
        # ── Label ─────────────────────────────────────────────────────────────
        label = _label_from_score(score)
 
        # ── Contributing factors ──────────────────────────────────────────────
        factors: List[str] = [
            f"Revenue variation (CV={cv:.2f}): {_cv_interpretation(cv)}",
            f"Top-5% spike share: {spike_ratio * 100:.0f}% of total revenue",
        ]
        if has_baseline and baseline_cv_delta_pct is not None and b_cv is not None:
            direction = "higher" if cv > b_cv else "lower"
            factors.append(
                f"Baseline volatility: {baseline_cv_delta_pct:.0f}% {direction} than prior period"
            )
 
        return RevenueStabilityResult(
            score=score,
            label=label,
            confidence=confidence,
            explanation=_build_explanation(score, cv, spike_ratio, has_baseline),
            contributing_factors=factors,
            warning=warning,
            coefficient_of_variation=round(cv, 4),
            spike_ratio=round(spike_ratio, 4),
            has_baseline_comparison=has_baseline,
        )
 
    except Exception:
        return None
