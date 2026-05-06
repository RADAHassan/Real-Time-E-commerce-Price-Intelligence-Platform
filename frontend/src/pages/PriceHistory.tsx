import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import {
  ArrowLeft,
  ExternalLink,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Area, AreaChart, CartesianGrid, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api/client'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'

const DAYS_OPTIONS = [7, 14, 30, 60, 90]

function fmt(price: number | undefined, currency: string | undefined) {
  if (!price || !currency) return '—'
  if (currency === 'MAD') return `${price.toLocaleString('fr-MA', { maximumFractionDigits: 2 })} MAD`
  try { return new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(price) }
  catch { return `${price.toFixed(2)} ${currency}` }
}

function KpiCard({ label, value, highlight }: { label: string; value: string; highlight?: 'up' | 'down' | 'neutral' }) {
  const valueColor =
    highlight === 'down'    ? 'text-emerald-400' :
    highlight === 'up'      ? 'text-red-400' :
    highlight === 'neutral' ? 'text-slate-400' :
    'text-slate-100'

  return (
    <div className="glass-card rounded-xl p-4">
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`text-lg font-bold tracking-tight ${valueColor}`}>{value}</p>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/95 px-4 py-3 shadow-xl backdrop-blur">
      <p className="mb-1.5 text-xs font-semibold text-slate-400">{label}</p>
      <p className="text-base font-bold text-gradient">{payload[0]?.value?.toFixed(2)}</p>
    </div>
  )
}

export default function PriceHistory() {
  const { productId } = useParams<{ productId: string }>()
  const nav = useNavigate()
  const [days, setDays] = useState(30)

  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => api.products.get(productId!),
    enabled: !!productId,
  })

  const { data: history, isLoading } = useQuery({
    queryKey: ['history', productId, days],
    queryFn: () => api.products.history(productId!, days),
    enabled: !!productId,
  })

  const first       = history?.[0]?.price
  const latest      = history?.[history.length - 1]?.price
  const periodHigh  = history ? Math.max(...history.map(h => h.price)) : undefined
  const periodLow   = history ? Math.min(...history.map(h => h.price)) : undefined
  const totalChange = first && latest ? ((latest - first) / first) * 100 : null
  const isDown      = totalChange !== null && totalChange < 0

  return (
    <div className="animate-slide-up space-y-6">
      {/* Back button */}
      <button
        onClick={() => nav(-1)}
        className="flex items-center gap-2 text-sm text-slate-500 transition hover:text-slate-300"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Live Prices
      </button>

      {/* Product header */}
      {product && (
        <div className="glass-card rounded-2xl p-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold leading-snug text-slate-100">{product.title}</h1>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <Badge source={product.source} />
                {product.category && (
                  <span className="text-xs text-slate-500">{product.category}</span>
                )}
              </div>
            </div>
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 flex items-center gap-1.5 btn-ghost text-xs"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              View Product
            </a>
          </div>
        </div>
      )}

      {/* KPI strip */}
      {history && history.length > 0 && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard label="Current Price" value={fmt(latest, product?.currency)} />
          <KpiCard label="Period High"   value={periodHigh?.toFixed(2) ?? '—'} highlight="up" />
          <KpiCard label="Period Low"    value={periodLow?.toFixed(2) ?? '—'}  highlight="down" />
          <KpiCard
            label="Total Change"
            value={totalChange != null ? `${totalChange > 0 ? '+' : ''}${totalChange.toFixed(2)}%` : '—'}
            highlight={isDown ? 'down' : totalChange !== null && totalChange > 0 ? 'up' : 'neutral'}
          />
        </div>
      )}

      {/* Day picker */}
      <div className="flex items-center gap-2">
        {DAYS_OPTIONS.map(d => (
          <button
            key={d}
            onClick={() => setDays(d)}
            className={clsx(
              'rounded-lg border px-3.5 py-1.5 text-sm font-medium transition',
              days === d
                ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-300'
                : 'border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-300'
            )}
          >
            {d}d
          </button>
        ))}
      </div>

      {isLoading && <Spinner label="Loading price history…" />}

      {/* Area chart */}
      {history && history.length > 0 && (
        <div className="glass-card rounded-2xl p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-200">Price Trend — {days} Day Window</h2>
            {totalChange !== null && (
              <span className={clsx(
                'flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-semibold',
                isDown
                  ? 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300'
                  : 'border-red-500/25 bg-red-500/10 text-red-300'
              )}>
                {isDown ? <TrendingDown className="h-3.5 w-3.5" /> : <TrendingUp className="h-3.5 w-3.5" />}
                {totalChange > 0 ? '+' : ''}{totalChange.toFixed(2)}%
              </span>
            )}
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={history} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" vertical={false} />
              <XAxis
                dataKey="scraped_date"
                stroke="transparent"
                tick={{ fontSize: 11, fill: '#475569' }}
                tickFormatter={v => v.slice(5)}
              />
              <YAxis
                stroke="transparent"
                tick={{ fontSize: 11, fill: '#475569' }}
                tickLine={false}
                width={56}
              />
              <Tooltip content={<CustomTooltip />} />
              {first && (
                <ReferenceLine
                  y={first}
                  stroke="rgba(99,102,241,0.3)"
                  strokeDasharray="4 4"
                  label={{ value: 'Start', position: 'right', fontSize: 10, fill: '#6366f1' }}
                />
              )}
              <Area
                type="monotone"
                dataKey="price"
                stroke="#6366f1"
                strokeWidth={2}
                fill="url(#priceGradient)"
                dot={false}
                activeDot={{ r: 5, fill: '#6366f1', strokeWidth: 2, stroke: '#020617' }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* History table */}
      {history && history.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-slate-800/60">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/60 bg-slate-900/60">
                {['Date', 'Price', 'Change', '% Change'].map(h => (
                  <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[...history].reverse().map((h, i) => {
                const isNeg = h.price_change_abs != null && h.price_change_abs < 0
                const isPos = h.price_change_abs != null && h.price_change_abs > 0
                return (
                  <tr key={i} className="table-row-hover border-b border-slate-800/30">
                    <td className="px-4 py-3 font-mono text-xs text-slate-500">{h.scraped_date}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-slate-200">{h.price.toFixed(2)}</td>
                    <td className={clsx('px-4 py-3 font-mono text-sm', isNeg ? 'text-emerald-400' : isPos ? 'text-red-400' : 'text-slate-600')}>
                      {h.price_change_abs != null
                        ? `${h.price_change_abs > 0 ? '+' : ''}${h.price_change_abs.toFixed(2)}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {h.price_change_pct != null ? (
                        <span className={clsx(
                          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium',
                          h.price_change_pct < 0
                            ? 'bg-emerald-500/10 text-emerald-300'
                            : 'bg-red-500/10 text-red-300'
                        )}>
                          {h.price_change_pct < 0
                            ? <TrendingDown className="h-3 w-3" />
                            : <TrendingUp className="h-3 w-3" />
                          }
                          {h.price_change_pct > 0 ? '+' : ''}{h.price_change_pct.toFixed(2)}%
                        </span>
                      ) : <span className="text-slate-700">—</span>}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
