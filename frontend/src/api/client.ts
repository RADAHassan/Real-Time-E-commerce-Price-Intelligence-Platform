import type { PriceAlert, PriceHistoryPoint, ProductListResponse, ProductPrice, SourceStats } from '../types'

const BASE = import.meta.env.VITE_API_URL ?? ''

async function get<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`)
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${await resp.text()}`)
  return resp.json() as Promise<T>
}

export const api = {
  products: {
    list: (params: { source?: string; search?: string; limit?: number; offset?: number } = {}) => {
      const qs = new URLSearchParams()
      if (params.source) qs.set('source', params.source)
      if (params.search) qs.set('search', params.search)
      if (params.limit)  qs.set('limit',  String(params.limit))
      if (params.offset) qs.set('offset', String(params.offset))
      return get<ProductListResponse>(`/api/v1/products?${qs}`)
    },
    get:     (id: string)                     => get<ProductPrice>(`/api/v1/products/${id}`),
    history: (id: string, days: number = 30)  => get<PriceHistoryPoint[]>(`/api/v1/products/${id}/history?days=${days}`),
  },
  sources: () => get<string[]>('/api/v1/sources'),
  stats:   ()  => get<SourceStats[]>('/api/v1/stats'),
  alerts:  (source?: string, minDrop = 5) => {
    const qs = new URLSearchParams({ min_drop_pct: String(minDrop) })
    if (source) qs.set('source', source)
    return get<PriceAlert[]>(`/api/v1/alerts?${qs}`)
  },
}
