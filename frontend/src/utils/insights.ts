/**
 * Safe insight extraction utility for backward compatibility
 * Handles multiple response structures from Service B
 */

interface BaseInsight {
  code?: string;
  severity?: string;
  title?: string;
  description?: string;
  affected_metric?: string;
  // V1.75+ enriched fields
  driver?: string;
  implication?: string;
  action_direction?: string;
  confidence?: string;
  confidence_basis?: string;
}

interface BusinessInsights {
  executive_takeaways?: string[];
  scope?: {
    analyzed: string[];
    not_analyzed: string[];
  };
  trend?: {
    direction?: string;
    description?: string;
    confidence?: string;
    driver?: string;
    implication?: string;
    action_direction?: string;
    confidence_basis?: string;
  };
  stability?: {
    category?: string;
    coefficient_of_variation?: number;
    description?: string;
    driver?: string;
    implication?: string;
    action_direction?: string;
    confidence?: string;
    confidence_basis?: string;
  };
  efficiency?: {
    signal?: string;
    description?: string;
    change_percent?: number;
    driver?: string;
    implication?: string;
    action_direction?: string;
    confidence?: string;
    confidence_basis?: string;
  };
  concentration?: {
    top_10_percent_contribution?: number;
    risk_level?: string;
    description?: string;
    driver?: string;
    implication?: string;
    action_direction?: string;
    confidence?: string;
    confidence_basis?: string;
  };
  executive_summary?: string;
  meta?: Record<string, any>;
}

interface InsightReport {
  summary?: string;
  metric_deltas?: any[];
  insights?: BaseInsight[];
}

export function extractInsights(report: any): BaseInsight[] {
  // Priority 1: report.insights (standard InsightEngine output)
  if (report?.insights && Array.isArray(report.insights)) {
    return report.insights;
  }

  // Priority 2: business_insights.enriched_insights (if exists)
  if (report?.business_insights?.enriched_insights && Array.isArray(report.business_insights.enriched_insights)) {
    return report.business_insights.enriched_insights;
  }

  // Priority 3: Extract from business insights structure
  if (report?.business_insights) {
    const bi = report.business_insights as BusinessInsights;
    const enriched: BaseInsight[] = [];

    // Extract from trend insight
    if (bi.trend) {
      enriched.push({
        code: 'TREND_ANALYSIS',
        severity: mapConfidenceToSeverity(bi.trend.confidence),
        title: 'Trend Analysis',
        description: bi.trend.description || '',
        affected_metric: 'revenue',
        driver: bi.trend.driver,
        implication: bi.trend.implication,
        action_direction: bi.trend.action_direction,
        confidence: bi.trend.confidence,
        confidence_basis: bi.trend.confidence_basis,
      });
    }

    // Extract from stability insight
    if (bi.stability) {
      enriched.push({
        code: 'STABILITY_ANALYSIS',
        severity: mapConfidenceToSeverity(bi.stability.confidence),
        title: 'Revenue Stability',
        description: bi.stability.description || '',
        affected_metric: 'revenue',
        driver: bi.stability.driver,
        implication: bi.stability.implication,
        action_direction: bi.stability.action_direction,
        confidence: bi.stability.confidence,
        confidence_basis: bi.stability.confidence_basis,
      });
    }

    // Extract from efficiency insight
    if (bi.efficiency) {
      enriched.push({
        code: 'EFFICIENCY_ANALYSIS',
        severity: mapConfidenceToSeverity(bi.efficiency.confidence),
        title: 'Revenue Efficiency',
        description: bi.efficiency.description || '',
        affected_metric: 'revenue',
        driver: bi.efficiency.driver,
        implication: bi.efficiency.implication,
        action_direction: bi.efficiency.action_direction,
        confidence: bi.efficiency.confidence,
        confidence_basis: bi.efficiency.confidence_basis,
      });
    }

    // Extract from concentration insight
    if (bi.concentration) {
      enriched.push({
        code: 'CONCENTRATION_ANALYSIS',
        severity: mapConfidenceToSeverity(bi.concentration.confidence),
        title: 'Revenue Concentration',
        description: bi.concentration.description || '',
        affected_metric: 'revenue',
        driver: bi.concentration.driver,
        implication: bi.concentration.implication,
        action_direction: bi.concentration.action_direction,
        confidence: bi.concentration.confidence,
        confidence_basis: bi.concentration.confidence_basis,
      });
    }

    if (enriched.length > 0) {
      return enriched;
    }
  }

  // Priority 4: generated_insights (fallback)
  if (report?.generated_insights && Array.isArray(report.generated_insights)) {
    return report.generated_insights;
  }

  // No insights found
  return [];
}

function mapConfidenceToSeverity(confidence?: string): string {
  if (!confidence) return 'low';
  
  const conf = confidence.toUpperCase();
  if (conf === 'HIGH') return 'high';
  if (conf === 'MEDIUM') return 'medium';
  return 'low';
}
