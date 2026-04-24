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
