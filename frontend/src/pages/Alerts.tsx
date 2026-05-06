import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { ArrowDownRight, Bell, ExternalLink, ShieldCheck, TrendingDown } from 'lucide-react'
import { useState } from 'react'
import { api } from '../api/client'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'
import type { PriceAlert } from '../types'

function fmt(price: number, currency: string) {
  if (currency === 'MAD') return `${price.toLocaleString('fr-MA', { maximumFractionDigits: 2 })} MAD`
  try { return new Intl.NumberFormat('en-GB', { style: 'currency', currency }).format(price) }
  catch { return `${price.toFixed(2)} ${currency}` }
}

type Severity = 'critical' | 'high' | 'medium'

function getSeverity(drop: number): Severity {
  if (drop >= 20) return 'critical'
  if (drop >= 10) return 'high'
  return 'medium'
}

const SEVERITY_META: Record<Severity, { label: string; badge: string; bar: string; text: string }> = {
  critical: {
    label: 'Critical',
    badge: 'bg-red-500/15 border-red-500/30 text-red-300',
    bar:   'bg-red-500',
    text:  'text-red-400',
  },
  high: {
    label: 'High',
    badge: 'bg-orange-500/15 border-orange-500/30 text-orange-300',
    bar:   'bg-orange-500',
    text:  'text-orange-400',
  },
  medium: {
    label: 'Medium',
    badge: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    bar:   'bg-amber-500',
    text:  'text-amber-400',
  },
}

function AlertCard({ a }: { a: PriceAlert }) {
  const drop     = Math.abs(a.price_change_pct)
  const severity = getSeverity(drop)
  const meta     = SEVERITY_META[severity]

  return (
    <div className={`glass-card rounded-2xl p-5 severity-${severity}`}>
      {/* Header */}
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge source={a.source} />
          <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${meta.badge}`}>
            <ArrowDownRight className="h-3 w-3" />
            {drop.toFixed(1)}% drop · {meta.label}
          </span>
        </div>
        <a
          href={a.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 text-slate-600 transition hover:text-indigo-400"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      {/* Title */}
      <p className="mb-4 line-clamp-2 text-sm font-medium leading-relaxed text-slate-200">
        {a.title}
      </p>

      {/* Drop bar */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-slate-600">Price drop severity</span>
          <span className={`text-xs font-bold ${meta.text}`}>{drop.toFixed(1)}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-slate-800">
          <div
            className={`h-full rounded-full transition-all ${meta.bar}`}
            style={{ width: `${Math.min(drop * 2, 100)}%` }}
          />
        </div>
      </div>

      {/* Price comparison */}
      <div className="flex items-end gap-3">
        <div className="flex-1">
          <p className="mb-0.5 text-xs text-slate-600">Current Price</p>
          <p className="text-xl font-bold text-gradient">{fmt(a.current_price, a.currency)}</p>
        </div>
        <TrendingDown className="mb-2 h-5 w-5 flex-shrink-0 text-slate-700" />
        <div className="flex-1 text-right">
          <p className="mb-0.5 text-xs text-slate-600">Was</p>
          <p className="text-sm font-medium text-slate-500 line-through">{fmt(a.prev_price, a.currency)}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-slate-800/40 pt-3">
        <span className="text-xs text-slate-600">Detected {a.alert_date}</span>
        <span className="text-xs font-semibold text-emerald-400">
          Save {fmt(Math.abs(a.price_change_abs), a.currency)}
        </span>
      </div>
    </div>
  )
}

const FILTER_OPTIONS = [
  { label: 'All Alerts', min: 5 },
  { label: 'High (≥10%)', min: 10 },
  { label: 'Critical (≥20%)', min: 20 },
]

export default function Alerts() {
  const [minDrop, setMinDrop] = useState(5)

  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['alerts', minDrop],
    queryFn: () => api.alerts(undefined, minDrop),
  })

  const critical = alerts?.filter(a => Math.abs(a.price_change_pct) >= 20).length ?? 0
  const high      = alerts?.filter(a => Math.abs(a.price_change_pct) >= 10 && Math.abs(a.price_change_pct) < 20).length ?? 0

  return (
    <div className="animate-slide-up">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-rose-500/25 bg-rose-500/10">
              <Bell className="h-4 w-4 text-rose-400" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-100">Price Alerts</h1>
          </div>
          <p className="text-sm text-slate-500">Products with significant price drops in the last 7 days</p>
        </div>

        {/* Summary pills */}
        {alerts && alerts.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 rounded-full border border-red-500/25 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-300">
              {critical} critical
            </span>
            <span className="flex items-center gap-1.5 rounded-full border border-orange-500/25 bg-orange-500/10 px-3 py-1.5 text-xs font-medium text-orange-300">
              {high} high
            </span>
          </div>
        )}
      </div>

      {/* Filter tabs */}
      <div className="mb-6 flex items-center gap-2">
        {FILTER_OPTIONS.map(opt => (
          <button
            key={opt.min}
            onClick={() => setMinDrop(opt.min)}
            className={clsx(
              'rounded-lg border px-4 py-1.5 text-sm font-medium transition',
              minDrop === opt.min
                ? 'border-indigo-500/40 bg-indigo-500/15 text-indigo-300'
                : 'border-slate-800 text-slate-500 hover:border-slate-700 hover:text-slate-300'
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {isLoading && <Spinner label="Scanning for price alerts…" />}

      {error && (
        <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center text-red-400 text-sm">
          Failed to load alerts
        </div>
      )}

      {alerts && alerts.length === 0 && (
        <div className="flex flex-col items-center gap-4 rounded-2xl border border-slate-800/50 bg-slate-900/30 py-20">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-500/20 bg-emerald-500/10">
            <ShieldCheck className="h-7 w-7 text-emerald-400" />
          </div>
          <div className="text-center">
            <p className="font-semibold text-slate-300">All clear</p>
            <p className="mt-1 text-sm text-slate-500">No price drops detected above {minDrop}% threshold.</p>
          </div>
        </div>
      )}

      {alerts && alerts.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {alerts.map(a => (
            <AlertCard key={`${a.product_id}-${a.alert_date}`} a={a} />
          ))}
        </div>
      )}
    </div>
  )
}
