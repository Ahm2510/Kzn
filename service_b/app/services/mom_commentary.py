import pandas as pd
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class MoMCommentaryResult(BaseModel):
    period_label: str                    # e.g., "Current vs Baseline" or "Current Period"
    revenue_current: float               # Current period total revenue
    revenue_baseline: Optional[float]    # Baseline period total revenue (None if no baseline)
    absolute_change: Optional[float]     # Current - Baseline
    percent_change: Optional[float]      # % change
    direction: str                       # "increase", "decrease", "flat", "no_baseline"
    magnitude: str                       # "significant", "moderate", "marginal", "flat", "no_baseline"
    is_meaningful: bool                  # Whether the change is statistically meaningful
    commentary: str                      # Business-readable paragraph (3-5 sentences)
    interpretation: str                  # One-line business interpretation
    driver_hint: Optional[str] = None    # What likely drove the change (if determinable)
    confidence: str = "medium"           # "high", "medium", "low"
    warning: Optional[str] = None        # Sample size or data quality warning
    sample_size: int = 0                 # Number of rows
    has_baseline: bool = False           # Whether a baseline was available

def _classify_direction(pct: Optional[float]) -> str:
    if pct is None:
        return "no_baseline"
    if pct > 2:
        return "increase"
    if pct < -2:
        return "decrease"
    return "flat"

def _classify_magnitude(pct: Optional[float]) -> str:
    if pct is None:
        return "no_baseline"
    abs_pct = abs(pct)
    if abs_pct > 20:
        return "significant"
    if abs_pct > 5:
        return "moderate"
    if abs_pct > 2:
        return "marginal"
    return "flat"

def _assess_meaningfulness(pct: Optional[float], cv: float, n: int) -> bool:
    if pct is None:
        return False
    # Change must exceed 2x the CV to be meaningful (signal > noise rule)
    noise_threshold = max(cv * 100 * 2, 3.0)  # at least 3%
    return abs(pct) > noise_threshold and n >= 20

def _build_driver_hint(direction: str, concentration: Optional[Dict[str, Any]], stability: Optional[Dict[str, Any]]) -> Optional[str]:
    driver_hint = None
    if concentration:
        risk = concentration.get("risk_level", "")
        top10 = concentration.get("top_10_percent_contribution", 0)
        if risk in ("high", "critical") and direction == "decrease":
            driver_hint = f"Revenue decline may be amplified by high concentration — top 10% drives {top10:.0f}% of revenue, so loss of a single large contributor can swing the total."
        elif risk in ("high", "critical") and direction == "increase":
            driver_hint = f"Revenue growth may be driven by a narrow slice — top 10% drives {top10:.0f}% of revenue. Validate whether growth is broad-based or single-contributor."
            
    if stability and stability.get("category") == "highly_volatile" and driver_hint is None:
        driver_hint = "High revenue volatility suggests the period-over-period change may reflect transaction spikes rather than sustained trend shifts."
    
    return driver_hint

def _build_interpretation(direction: str, magnitude: str, pct: Optional[float], revenue_current: float, n: int) -> str:
    if direction == "no_baseline":
        return f"Current period revenue is ${revenue_current:,.0f} across {n:,} transactions. No baseline available for comparison."
    
    pct_val = pct or 0.0
    if magnitude == "significant" and direction == "increase":
        return f"Revenue grew significantly by {pct_val:+.1f}% — this is a strong positive signal that warrants investigation into what drove the growth."
    elif magnitude == "significant" and direction == "decrease":
        return f"Revenue declined significantly by {pct_val:+.1f}% — this is a concerning signal that requires immediate root cause analysis."
    elif magnitude == "moderate" and direction == "increase":
        return f"Revenue increased moderately by {pct_val:+.1f}% — a positive but not exceptional movement."
    elif magnitude == "moderate" and direction == "decrease":
        return f"Revenue declined moderately by {pct_val:+.1f}% — worth monitoring but not yet alarming."
    elif magnitude == "marginal":
        return f"Revenue shifted marginally by {pct_val:+.1f}% — this may be noise rather than a meaningful trend."
    
    return f"Revenue is essentially flat ({pct_val:+.1f}%) — no meaningful change detected between periods."

def _build_commentary(
    has_baseline: bool, 
    revenue_baseline: Optional[float], 
    revenue_current: float, 
    pct_change: Optional[float], 
    absolute_change: Optional[float],
    n: int,
    is_meaningful: bool,
    direction: str,
    driver_hint: Optional[str],
    warning: Optional[str]
) -> str:
    parts = []
    
    # Sentence 1: The headline
    if has_baseline and revenue_baseline is not None and pct_change is not None and absolute_change is not None:
        parts.append(f"Revenue moved from ${revenue_baseline:,.0f} to ${revenue_current:,.0f}, a {pct_change:+.1f}% change ({'+' if absolute_change >= 0 else ''}{absolute_change:,.0f} in absolute terms).")
    else:
        parts.append(f"Current period revenue totals ${revenue_current:,.0f} across {n:,} transactions.")
    
    # Sentence 2: Meaningfulness
    if is_meaningful and direction in ("increase", "decrease"):
        parts.append(f"This {direction} appears meaningful — it exceeds normal variability in the data and is likely signal rather than noise.")
    elif not is_meaningful and has_baseline:
        parts.append("This change is within the range of normal variability and may not reflect a true shift in business performance.")
    
    # Sentence 3: Driver hint (if available)
    if driver_hint:
        parts.append(driver_hint)
    
    # Sentence 4: What to do
    if direction == "increase" and is_meaningful:
        parts.append("Leadership should identify the source of growth and assess its repeatability before committing incremental investment.")
    elif direction == "decrease" and is_meaningful:
        parts.append("Leadership should conduct a rapid root cause review — check customer retention, pricing changes, and product availability in the period.")
    elif direction == "flat":
        parts.append("A flat revenue line is not inherently negative but may indicate missed growth opportunities in a favorable market.")
    elif not has_baseline:
        parts.append("Consider uploading a baseline period to enable comparative analysis and trend detection.")
    
    # Sentence 5: Warning if applicable
    if warning:
        parts.append(f"Note: {warning}")
    
    return " ".join(parts)

def compute_mom_commentary(
    current_df: pd.DataFrame,
    baseline_df: Optional[pd.DataFrame],
    revenue_column: str,
    baseline_revenue_column: Optional[str],
    stability: Optional[Dict[str, Any]] = None,
    concentration: Optional[Dict[str, Any]] = None,
) -> Optional[MoMCommentaryResult]:
    """
    Computes structured MoM commentary based on current and baseline data.
    """
    try:
        # Step 1: Revenue Extraction
        current_rev = pd.to_numeric(current_df[revenue_column], errors="coerce").dropna()
        revenue_current = float(current_rev.sum())
        n = len(current_rev)
        
        if baseline_df is not None and baseline_revenue_column and baseline_revenue_column in baseline_df.columns:
            baseline_rev = pd.to_numeric(baseline_df[baseline_revenue_column], errors="coerce").dropna()
            revenue_baseline = float(baseline_rev.sum())
            has_baseline = True
        else:
            revenue_baseline = None
            has_baseline = False
            
        # Step 2: Delta Computation
        if has_baseline and revenue_baseline is not None and revenue_baseline > 0:
            absolute_change = revenue_current - revenue_baseline
            percent_change = (absolute_change / revenue_baseline) * 100
        else:
            absolute_change = None
            percent_change = None
            
        # Step 3: Direction & Magnitude
        direction = _classify_direction(percent_change)
        magnitude = _classify_magnitude(percent_change)
        
        # Step 4: Meaningfulness
        cv = stability.get("coefficient_of_variation", 0.5) if stability else 0.5
        is_meaningful = _assess_meaningfulness(percent_change, cv, n)
        
        # Step 5: Confidence
        if n >= 500 and has_baseline:
            confidence = "high"
        elif n >= 50:
            confidence = "medium"
        else:
            confidence = "low"
            
        # Step 6: Warning
        warning = None
        if n < 20:
            warning = f"Very small sample size ({n} transactions) — commentary is directional only."
        elif n < 50:
            warning = f"Small sample size ({n} transactions) reduces confidence in period comparison."
        elif not has_baseline:
            warning = "No baseline period provided — commentary reflects current period only."
            
        # Step 7: Driver Hint
        driver_hint = _build_driver_hint(direction, concentration, stability)
        
        # Step 8: Interpretation
        interpretation = _build_interpretation(direction, magnitude, percent_change, revenue_current, n)
        
        # Step 9: Full Commentary
        commentary = _build_commentary(
            has_baseline, revenue_baseline, revenue_current, percent_change, absolute_change,
            n, is_meaningful, direction, driver_hint, warning
        )
        
        return MoMCommentaryResult(
            period_label="Current vs Baseline" if has_baseline else "Current Period",
            revenue_current=round(revenue_current, 2),
            revenue_baseline=round(revenue_baseline, 2) if revenue_baseline is not None else None,
            absolute_change=round(absolute_change, 2) if absolute_change is not None else None,
            percent_change=round(percent_change, 2) if percent_change is not None else None,
            direction=direction,
            magnitude=magnitude,
            is_meaningful=is_meaningful,
            commentary=commentary,
            interpretation=interpretation,
            driver_hint=driver_hint,
            confidence=confidence,
            warning=warning,
            sample_size=n,
            has_baseline=has_baseline,
        )
    except Exception:
        return None
