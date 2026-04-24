import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ExternalLink, TrendingDown } from 'lucide-react'
import { api } from '../api/client'
import Badge from '../components/Badge'
import Spinner from '../components/Spinner'
import type { PriceAlert } from '../types'

function AlertCard({ a }: { a: PriceAlert }) {
  const drop = Math.abs(a.price_change_pct)
  const severity = drop >= 20 ? 'border-red-700 bg-red-950/30' : drop >= 10 ? 'border-orange-700 bg-orange-950/20' : 'border-yellow-700 bg-yellow-950/20'

  return (
    <div className={`rounded-xl border p-5 ${severity}`}>
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge source={a.source} />
          <span className="rounded-full bg-red-900/60 px-2 py-0.5 text-xs font-bold text-red-300">
            ↓ {drop.toFixed(1)}% drop
          </span>
        </div>
        <a
          href={a.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-slate-500 hover:text-slate-300"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      <p className="mb-3 line-clamp-2 font-medium text-slate-100">{a.title}</p>

      <div className="flex items-end gap-4">
        <div>
          <p className="text-xs text-slate-500">Current</p>
          <p className="text-xl font-bold text-green-400">
            {a.current_price.toFixed(2)} {a.currency}
          </p>
        </div>
        <TrendingDown className="mb-1 h-5 w-5 text-slate-600" />
        <div>
          <p className="text-xs text-slate-500">Was</p>
          <p className="text-lg font-medium text-slate-400 line-through">
            {a.prev_price.toFixed(2)} {a.currency}
          </p>
        </div>
        <div className="ml-auto text-right">
          <p className="text-xs text-slate-500">Saved</p>
          <p className="font-bold text-green-400">
            {Math.abs(a.price_change_abs).toFixed(2)} {a.currency}
          </p>
        </div>
      </div>

      <p className="mt-2 text-xs text-slate-600">Detected {a.alert_date}</p>
    </div>
  )
}

export default function Alerts() {
  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.alerts(),
  })

  return (
    <div>
      <div className="mb-6 flex items-center gap-3">
        <AlertTriangle className="h-6 w-6 text-orange-400" />
        <div>
          <h1 className="text-2xl font-bold">Price Alerts</h1>
          <p className="mt-0.5 text-sm text-slate-400">
            Products with a significant price drop in the last 7 days
          </p>
        </div>
      </div>

      {isLoading && <Spinner label="Checking for alerts…" />}
      {error && <p className="text-red-400">Failed to load alerts</p>}

      {alerts && alerts.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 py-16 text-center text-slate-500">
          <p className="text-4xl">✅</p>
          <p className="mt-3">No significant price drops detected right now.</p>
        </div>
      )}

      {alerts && alerts.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {alerts.map(a => <AlertCard key={`${a.product_id}-${a.alert_date}`} a={a} />)}
        </div>
      )}
    </div>
  )
}
