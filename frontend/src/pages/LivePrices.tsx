import { useQuery } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'
import type { ProductPrice } from '../types'

const SOURCES = ['all', 'books.toscrape.com', 'scrapeme.live', 'jumia.ma', 'ultrapc.ma', 'micromagma.ma']

function fmt(price: number, currency: string) {
  return currency === 'MAD'
    ? `${price.toLocaleString('fr-MA')} MAD`
    : new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(price)
}

function Stars({ rating }: { rating?: number }) {
  if (!rating) return null
  const full = Math.round(rating)
  return (
    <span className="text-xs text-yellow-400">
      {'★'.repeat(full)}{'☆'.repeat(5 - full)} {rating.toFixed(1)}
    </span>
  )
}

function ProductCard({ p }: { p: ProductPrice }) {
  const nav = useNavigate()
  return (
    <div
      onClick={() => nav(`/history/${p.product_id}`)}
      className="cursor-pointer rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-blue-700 hover:bg-slate-800"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <Badge source={p.source} />
        <span className={`text-xs font-medium ${p.availability === 'In Stock' ? 'text-green-400' : 'text-red-400'}`}>
          {p.availability}
        </span>
      </div>
      <p className="mb-1 line-clamp-2 text-sm font-medium text-slate-100">{p.title}</p>
      {p.category && <p className="mb-2 text-xs text-slate-500">{p.category}</p>}
      <Stars rating={p.rating} />
      <div className="mt-3 flex items-end justify-between">
        <span className="text-lg font-bold text-blue-400">{fmt(p.price, p.currency)}</span>
        <span className="text-xs text-slate-600">{p.scraped_date}</span>
      </div>
    </div>
  )
}

export default function LivePrices() {
  const [source, setSource] = useState('all')
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['products', source, debouncedSearch],
    queryFn: () => api.products.list({
      source: source !== 'all' ? source : undefined,
      search: debouncedSearch || undefined,
      limit: 200,
    }),
  })

  const handleSearch = (v: string) => {
    setSearch(v)
    clearTimeout((handleSearch as any)._t)
    ;(handleSearch as any)._t = setTimeout(() => setDebouncedSearch(v), 350)
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Live Prices</h1>
          <p className="mt-1 text-sm text-slate-400">
            {data ? `${data.total} products tracked` : 'Loading…'}
          </p>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={search}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search products…"
            className="w-64 rounded-lg border border-slate-700 bg-slate-900 py-2 pl-9 pr-4 text-sm outline-none focus:border-blue-600"
          />
        </div>
      </div>

      {/* Source filter pills */}
      <div className="mb-6 flex flex-wrap gap-2">
        {SOURCES.map(s => (
          <button
            key={s}
            onClick={() => setSource(s)}
            className={`rounded-full px-3 py-1 text-sm transition ${
              source === s
                ? 'bg-blue-600 text-white'
                : 'border border-slate-700 text-slate-400 hover:border-slate-600 hover:text-slate-200'
            }`}
          >
            {s === 'all' ? 'All sources' : s}
          </button>
        ))}
      </div>

      {isLoading && <Spinner label="Fetching prices…" />}
      {error && <p className="text-red-400">Error: {String(error)}</p>}

      {data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {data.items.map(p => <ProductCard key={p.product_id} p={p} />)}
        </div>
      )}
    </div>
  )
}
