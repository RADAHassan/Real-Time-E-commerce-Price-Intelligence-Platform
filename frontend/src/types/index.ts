export interface ProductPrice {
  product_id: string
  source: string
  title: string
  url: string
  price: number
  currency: string
  rating?: number
  availability: string
  category?: string
  scraped_at: string
  scraped_date: string
}

export interface ProductListResponse {
  items: ProductPrice[]
  total: number
  source_filter?: string
  search?: string
}

export interface PriceHistoryPoint {
  product_id: string
  price: number
  prev_price?: number
  price_change_pct?: number
  price_change_abs?: number
  scraped_date: string
  scraped_at: string
}

export interface SourceStats {
  source: string
  currency: string
  product_count: number
  observation_count: number
  avg_price: number
  min_price: number
  max_price: number
  median_price: number
  p25_price: number
  p75_price: number
  stddev_price?: number
  first_seen_date: string
  last_updated_date: string
}

// ── Statistical Analysis ──────────────────────────────────────────────────

export interface DescriptiveStat {
  source: string
  n: number
  mean: number
  median: number
  std: number
  min: number
  max: number
  q25: number
  q75: number
  skew: number | null
  kurtosis: number | null
  cv: number
}

export interface NormalityTest {
  source: string
  n: number
  w_stat: number
  p_value: number
  is_normal: boolean
}

export interface MannWhitneyPair {
  source_a: string
  source_b: string
  u_stat: number
  p_value: number
  effect_r: number
  significant: boolean
}

export interface ConfidenceInterval {
  source: string
  n: number
  mean: number
  ci_lower: number
  ci_upper: number
  ci_width: number
  rel_width: number
}

export interface HypothesisTests {
  normality: NormalityTest[]
  anova: { f_stat: number; p_value: number; reject: boolean }
  kruskal: { h_stat: number; p_value: number; reject: boolean }
  pairwise: MannWhitneyPair[]
  confidence_intervals: ConfidenceInterval[]
  sources: string[]
}

export interface ScatterPoint {
  rating: number
  price: number
  source: string
}

export interface PerSourceRegression {
  source: string
  n: number
  slope: number
  intercept: number
  r: number
  r2: number
  p_value: number
  significant: boolean
}

export interface RegressionResult {
  slope: number
  intercept: number
  r: number
  r2: number
  p_value: number
  se: number
  n: number
  scatter: ScatterPoint[]
  ols_line: { rating: number; price: number }[]
  per_source: PerSourceRegression[]
}

export interface PriceAlert {
  product_id: string
  source: string
  title: string
  url: string
  currency: string
  current_price: number
  prev_price: number
  price_change_pct: number
  price_change_abs: number
  alert_date: string
  scraped_at: string
}
