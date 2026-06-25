/**
 * Indian-currency + number formatting for the distribution niche.
 * Mirrors service_b/app/services/insight_engine/entity_detector.format_inr*.
 */

/** ₹ with Indian digit grouping, e.g. ₹12,34,567 */
export function formatINR(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return "₹0";
  const negative = amount < 0;
  let whole = Math.round(Math.abs(amount)).toString();
  if (whole.length > 3) {
    const last3 = whole.slice(-3);
    const rest = whole.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",");
    whole = `${rest},${last3}`;
  }
  return `${negative ? "-" : ""}₹${whole}`;
}

/** Lakh / crore shorthand familiar to Indian SMBs, e.g. ₹4.2L, ₹1.5 Cr */
export function formatINRLakh(amount: number | null | undefined): string {
  if (amount == null || Number.isNaN(amount)) return "₹0";
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "-" : "";
  if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toFixed(1)} Cr`;
  if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(1)}L`;
  return formatINR(amount);
}

/** Plain integer with thousands separators (locale-aware). */
export function formatCount(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return "0";
  return Math.round(n).toLocaleString("en-IN");
}
