import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  ArrowUpDown,
  ChevronRight,
  ExternalLink,
  Search,
  SlidersHorizontal,
  Star,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import Badge from '../components/Badge'
import { SkeletonRow } from '../components/Spinner'
import type { ProductPrice, SourceStats } from '../types'

// ── Source colours & labels ───────────────────────────────────────────────────
const SRC_COLOR: Record<string, string> = {
  'books.toscrape.com': '#6366f1',
  'scrapeme.live':      '#f59e0b',
  'jumia.ma':           '#fb923c',
  'ultrapc.ma':         '#22d3ee',
  'micromagma.ma':      '#34d399',
  'cdiscount.com':      '#f43f5e',
}
const srcColor = (s: string) => SRC_COLOR[s] ?? '#6366f1'

const SOURCES = ['all', 'books.toscrape.com', 'scrapeme.live', 'jumia.ma', 'ultrapc.ma', 'micromagma.ma', 'cdiscount.com']

type SortKey = 'price_asc' | 'price_desc' | 'rating_desc' | 'title_asc'
const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: 'price_asc',   label: 'Price: Low → High' },
  { key: 'price_desc',  label: 'Price: High → Low' },
  { key: 'rating_desc', label: 'Top Rated' },
  { key: 'title_asc',   label: 'Name A → Z' },
]

function fmtPrice(price: number, currency: string) {
  if (currency === 'MAD') return `${price.toLocaleString('fr-MA', { maximumFractionDigits: 2 })} MAD`
  try { return new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(price) }
  catch { return `${price.toFixed(2)} ${currency}` }
}

function RatingStars({ rating }: { rating?: number }) {
  if (!rating) return <span className="text-slate-600">—</span>
  return (
    <span className="flex items-center gap-1">
      <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
      <span className="font-mono text-xs text-amber-300">{rating.toFixed(1)}</span>
    </span>
  )
}

function AvailabilityPill({ status }: { status: string }) {
  const inStock = status.toLowerCase().includes('stock') && !status.toLowerCase().includes('out')
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
      inStock
        ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20'
        : 'bg-red-500/10 text-red-300 border border-red-500/20'
    )}>
      <span className={clsx('h-1.5 w-1.5 rounded-full', inStock ? 'bg-emerald-400' : 'bg-red-400')} />
      {inStock ? 'In Stock' : 'Out of Stock'}
    </span>
  )
}

function sortProducts(items: ProductPrice[], sort: SortKey): ProductPrice[] {
  return [...items].sort((a, b) => {
    if (sort === 'price_asc')   return a.price - b.price
    if (sort === 'price_desc')  return b.price - a.price
    if (sort === 'rating_desc') return (b.rating ?? 0) - (a.rating ?? 0)
    return a.title.localeCompare(b.title)
  })
}

// ── Market share donut ────────────────────────────────────────────────────────
function MarketShareDonut({ stats }: { stats: SourceStats[] }) {
  const total = stats.reduce((s, r) => s + r.product_count, 0)
  const slices = stats.map(r => ({ name: r.source, value: r.product_count }))

  const renderCenterLabel = ({ cx, cy }: any) => (
    <text>
      <tspan x={cx} y={cy - 10} textAnchor="middle" fontSize={22} fontWeight={800} fill="#f1f5f9">
        {total.toLocaleString()}
      </tspan>
      <tspan x={cx} y={cy + 12} textAnchor="middle" fontSize={10} fill="#475569">
        products
      </tspan>
    </text>
  )

  return (
    <div className="glass-card rounded-2xl p-5">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-slate-200">Market Share</h3>
        <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-xs font-semibold text-slate-500">
          by product count
        </span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={slices}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={90}
            paddingAngle={3}
            dataKey="value"
            labelLine={false}
            label={renderCenterLabel}
          >
            {slices.map(s => (
              <Cell key={s.name} fill={srcColor(s.name)} fillOpacity={0.85} stroke="transparent" />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, fontSize: 12 }}
            formatter={(v: number, name: string) => [
              `${v.toLocaleString()} (${((v / total) * 100).toFixed(1)}%)`,
              name.split('.')[0],
            ]}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5">
        {stats.map(r => (
          <span key={r.source} className="flex items-center gap-1.5 text-xs text-slate-500">
            <span className="h-2 w-2 rounded-sm flex-shrink-0" style={{ background: srcColor(r.source) }} />
            {r.source.split('.')[0]}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Price ranges chart ────────────────────────────────────────────────────────
function PriceRangesChart({ stats }: { stats: SourceStats[] }) {
  const data = stats.map(r => ({
    name: r.source.split('.')[0],
    Min:    +r.min_price.toFixed(2),
    Avg:    +r.avg_price.toFixed(2),
    Median: +r.median_price.toFixed(2),
    Max:    +r.max_price.toFixed(2),
  }))

  return (
    <div className="glass-card rounded-2xl p-5">
      <div className="mb-3 flex items-center gap-2">
        <h3 className="text-sm font-semibold text-slate-200">Price Ranges by Source</h3>
        <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-xs font-semibold text-slate-500">
          min · avg · median · max
        </span>
        <span className="ml-auto text-xs text-slate-600">currencies vary by source</span>
      </div>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} barGap={2} barCategoryGap="28%"
                  margin={{ left: -4, right: 8, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" vertical={false} />
          <XAxis dataKey="name" stroke="transparent"
                 tick={{ fontSize: 10, fill: '#475569' }} tickLine={false} />
          <YAxis stroke="transparent" tick={{ fontSize: 10, fill: '#475569' }} tickLine={false} width={40} />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, fontSize: 12 }}
            labelStyle={{ color: '#94a3b8' }}
          />
          <Legend wrapperStyle={{ fontSize: 11, color: '#475569', paddingTop: 8 }} />
          <Bar dataKey="Min"    fill="#22d3ee" fillOpacity={0.8} radius={[3, 3, 0, 0]} />
          <Bar dataKey="Avg"    fill="#818cf8" fillOpacity={0.8} radius={[3, 3, 0, 0]} />
          <Bar dataKey="Median" fill="#34d399" fillOpacity={0.8} radius={[3, 3, 0, 0]} />
          <Bar dataKey="Max"    fill="#f87171" fillOpacity={0.8} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Source intelligence table ─────────────────────────────────────────────────
function SourceIntelligenceTable({ stats }: { stats: SourceStats[] }) {
  const total = stats.reduce((s, r) => s + r.product_count, 0)
  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-slate-800/60">
        <h3 className="text-sm font-semibold text-slate-200">Source Intelligence</h3>
        <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-xs font-semibold text-slate-500">
          {stats.length} sources
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800/40 bg-slate-900/40">
              {['Source', 'Currency', 'Products', 'Avg Price', 'Min', 'Median', 'Max'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-600">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.sort((a, b) => b.product_count - a.product_count).map((r, i) => {
              const pct = total > 0 ? (r.product_count / total) * 100 : 0
              const col = srcColor(r.source)
              return (
                <tr key={r.source} className={clsx(
                  'border-b border-slate-800/20',
                  i % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20',
                )}>
                  <td className="px-4 py-3.5">
                    <span className="flex items-center gap-2">
                      <span className="h-2.5 w-2.5 rounded-full flex-shrink-0" style={{ background: col }} />
                      <span className="font-medium text-slate-200">{r.source}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="rounded-full border px-2.5 py-0.5 text-xs font-bold"
                          style={{ color: col, borderColor: `${col}55`, background: `${col}15` }}>
                      {r.currency}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-20 h-1 rounded-full bg-slate-800 overflow-hidden flex-shrink-0">
                        <div className="h-full rounded-full transition-all"
                             style={{ width: `${pct.toFixed(1)}%`, background: col }} />
                      </div>
                      <span className="font-mono text-xs font-semibold text-slate-300">
                        {r.product_count.toLocaleString()}
                      </span>
                      <span className="text-xs text-slate-600">({pct.toFixed(1)}%)</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-sm font-bold" style={{ color: col }}>
                    {r.avg_price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-sm text-emerald-400 font-semibold">
                    {r.min_price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-sm text-slate-400">
                    {r.median_price.toFixed(2)}
                  </td>
                  <td className="px-4 py-3.5 font-mono text-sm text-rose-400 font-semibold">
                    {r.max_price.toFixed(2)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function LivePrices() {
  const nav = useNavigate()
  const [source, setSource]             = useState('all')
  const [search, setSearch]             = useState('')
  const [debouncedSearch, setDebounced] = useState('')
  const [sort, setSort]                 = useState<SortKey>('price_asc')
  const [showSortMenu, setShowSortMenu] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout>>()

  const { data, isLoading, error } = useQuery({
    queryKey: ['products', source, debouncedSearch],
    queryFn: () => api.products.list({
      source: source !== 'all' ? source : undefined,
      search: debouncedSearch || undefined,
      limit: 300,
    }),
  })

  const { data: statsData } = useQuery({
    queryKey: ['stats'],
    queryFn: api.stats,
    staleTime: 5 * 60 * 1000,
  })

  const handleSearch = (v: string) => {
    setSearch(v)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => setDebounced(v), 350)
  }

  const sorted = useMemo(() => sortProducts(data?.items ?? [], sort), [data, sort])
  const currentSort = SORT_OPTIONS.find(o => o.key === sort)!

  return (
    <div className="animate-slide-up">
      {/* Page header */}
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Live Prices</h1>
          <p className="mt-1 text-sm text-slate-500">
            {data ? (
              <><span className="text-indigo-400 font-medium">{data.total.toLocaleString()}</span> products tracked across {SOURCES.length - 1} sources</>
            ) : 'Loading product catalog…'}
          </p>
        </div>

        {/* Search + Sort */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500 pointer-events-none" />
            <input
              value={search}
              onChange={e => handleSearch(e.target.value)}
              placeholder="Search products…"
              className="w-60 rounded-lg border border-slate-800 bg-slate-900/80 py-2 pl-9 pr-4 text-sm text-slate-100 placeholder-slate-500 outline-none transition focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20"
            />
          </div>

          <div className="relative">
            <button
              onClick={() => setShowSortMenu(v => !v)}
              className="btn-ghost flex items-center gap-2"
            >
              <ArrowUpDown className="h-3.5 w-3.5" />
              <span>{currentSort.label}</span>
            </button>
            {showSortMenu && (
              <div className="absolute right-0 top-full mt-1 z-20 min-w-[180px] rounded-xl border border-slate-700/50 bg-slate-900 p-1 shadow-xl">
                {SORT_OPTIONS.map(o => (
                  <button
                    key={o.key}
                    onClick={() => { setSort(o.key); setShowSortMenu(false) }}
                    className={clsx(
                      'w-full rounded-lg px-3 py-2 text-left text-sm transition',
                      o.key === sort
                        ? 'bg-indigo-500/15 text-indigo-300'
                        : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                    )}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Market overview charts ── */}
      {statsData && statsData.length > 0 && (
        <div className="mb-6 space-y-4">
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <MarketShareDonut stats={statsData} />
            <PriceRangesChart stats={statsData} />
          </div>
          <SourceIntelligenceTable stats={statsData} />
        </div>
      )}

      {/* ── Source filter chips (below charts, above product table) ── */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <SlidersHorizontal className="h-3.5 w-3.5 text-slate-600 mr-1 flex-shrink-0" />
        <button
          onClick={() => setSource('all')}
          className={clsx(
            'rounded-full border px-3.5 py-1 text-xs font-medium transition',
            source === 'all'
              ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-300'
              : 'border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-300'
          )}
        >
          All Sources
        </button>
        {(statsData ?? SOURCES.filter(s => s !== 'all').map(s => ({ source: s }))).map((item) => {
          const s = typeof item === 'string' ? item : (item as any).source
          const col = srcColor(s)
          const active = source === s
          return (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={clsx(
                'flex items-center gap-1.5 rounded-full border px-3.5 py-1 text-xs font-medium transition',
                active ? 'text-slate-100' : 'border-slate-800 text-slate-500 hover:border-slate-600 hover:text-slate-300'
              )}
              style={active ? { borderColor: `${col}66`, background: `${col}18`, color: col } : {}}
            >
              <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: col }} />
              {s}
            </button>
          )
        })}
      </div>

      {/* ── Product table ── */}
      <div className="overflow-hidden rounded-2xl border border-slate-800/60 bg-slate-900/40">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/60">
                {['Product', 'Source', 'Price', 'Category', 'Rating', 'Availability', 'Last Updated', ''].map(h => (
                  <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading && Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)}

              {!isLoading && sorted.map((p, idx) => (
                <tr
                  key={p.product_id}
                  onClick={() => nav(`/history/${p.product_id}`)}
                  className={clsx(
                    'table-row-hover cursor-pointer border-b border-slate-800/30',
                    idx % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20'
                  )}
                >
                  <td className="px-4 py-3.5 max-w-xs">
                    <span className="line-clamp-1 font-medium text-slate-200 group-hover:text-white">
                      {p.title}
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <Badge source={p.source} />
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="font-mono text-sm font-semibold text-gradient">
                      {fmtPrice(p.price, p.currency)}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-slate-500 text-xs">
                    {p.category || '—'}
                  </td>
                  <td className="px-4 py-3.5">
                    <RatingStars rating={p.rating} />
                  </td>
                  <td className="px-4 py-3.5">
                    <AvailabilityPill status={p.availability} />
                  </td>
                  <td className="px-4 py-3.5 font-mono text-xs text-slate-600">
                    {p.scraped_date}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <a
                        href={p.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={e => e.stopPropagation()}
                        className="text-slate-600 transition hover:text-indigo-400"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                      <ChevronRight className="h-3.5 w-3.5 text-slate-700" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {!isLoading && sorted.length === 0 && (
          <div className="py-20 text-center">
            <Search className="mx-auto mb-3 h-10 w-10 text-slate-700" />
            <p className="text-slate-500">No products match your filters.</p>
          </div>
        )}

        {error && (
          <div className="py-12 text-center text-red-400 text-sm">
            Failed to load products — {String(error)}
          </div>
        )}

        {/* Footer */}
        {!isLoading && sorted.length > 0 && (
          <div className="flex items-center justify-between border-t border-slate-800/40 px-4 py-3">
            <span className="text-xs text-slate-600">
              Showing {sorted.length.toLocaleString()} of {(data?.total ?? 0).toLocaleString()} products
            </span>
            <div className="flex items-center gap-1">
              {[TrendingUp, TrendingDown].map((Icon, i) => (
                <span key={i} className="rounded-md p-1 text-slate-700">
                  <Icon className="h-3.5 w-3.5" />
                </span>
              ))}
              <span className="text-xs text-slate-600 ml-1">Click any row for price history</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
