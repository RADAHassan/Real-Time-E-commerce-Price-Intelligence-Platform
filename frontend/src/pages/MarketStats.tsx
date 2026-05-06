import { useQuery } from '@tanstack/react-query'
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api/client'
import { SourceDot } from '../components/Badge'
import Spinner from '../components/Spinner'
import type { SourceStats } from '../types'

const SOURCE_PALETTE = ['#6366f1', '#8b5cf6', '#a855f7', '#22d3ee', '#10b981', '#f59e0b']

function KpiCard({
  label, value, sub, accent = false,
}: { label: string; value: string; sub?: string; accent?: boolean }) {
  return (
    <div className={`glass-card rounded-2xl p-5 ${accent ? 'border-indigo-500/25' : ''}`}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`text-2xl font-bold tracking-tight ${accent ? 'text-gradient' : 'text-slate-100'}`}>
        {value}
      </p>
      {sub && <p className="mt-1 text-xs text-slate-600">{sub}</p>}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/95 px-4 py-3 shadow-xl backdrop-blur">
      <p className="mb-2 text-xs font-semibold text-slate-400">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center justify-between gap-4 text-sm">
          <span className="text-slate-500">{p.name}</span>
          <span className="font-mono font-semibold text-slate-100">{p.value.toFixed(2)}</span>
        </p>
      ))}
    </div>
  )
}

function StatsTable({ stats }: { stats: SourceStats[] }) {
  const cols = [
    { key: 'source',        label: 'Source' },
    { key: 'currency',      label: 'Currency' },
    { key: 'product_count', label: 'Products' },
    { key: 'avg_price',     label: 'Avg' },
    { key: 'median_price',  label: 'Median' },
    { key: 'min_price',     label: 'Min' },
    { key: 'max_price',     label: 'Max' },
    { key: 'stddev_price',  label: 'Std Dev' },
  ]

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800/60">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-800/60 bg-slate-900/60">
            {cols.map(c => (
              <th key={c.key} className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
            <tr key={s.source} className="table-row-hover border-b border-slate-800/30">
              <td className="px-4 py-3.5">
                <span className="flex items-center gap-2.5">
                  <SourceDot source={s.source} />
                  <span className="font-medium text-slate-200">{s.source}</span>
                </span>
              </td>
              <td className="px-4 py-3.5">
                <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 font-mono text-xs text-slate-400">
                  {s.currency}
                </span>
              </td>
              <td className="px-4 py-3.5 font-mono text-slate-300">{s.product_count.toLocaleString()}</td>
              <td className="px-4 py-3.5 font-mono font-semibold text-gradient">{s.avg_price.toFixed(2)}</td>
              <td className="px-4 py-3.5 font-mono text-slate-300">{s.median_price.toFixed(2)}</td>
              <td className="px-4 py-3.5 font-mono text-emerald-400">{s.min_price.toFixed(2)}</td>
              <td className="px-4 py-3.5 font-mono text-rose-400">{s.max_price.toFixed(2)}</td>
              <td className="px-4 py-3.5 font-mono text-slate-500">{s.stddev_price?.toFixed(2) ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function MarketStats() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: api.stats,
  })

  if (isLoading) return <Spinner label="Loading market statistics…" />
  if (error || !stats) return (
    <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center text-red-400 text-sm">
      Failed to load statistics
    </div>
  )

  const totalProducts = stats.reduce((s, r) => s + r.product_count, 0)
  const totalObs      = stats.reduce((s, r) => s + r.observation_count, 0)
  const globalAvg     = stats.reduce((s, r) => s + r.avg_price * r.product_count, 0) / Math.max(totalProducts, 1)

  return (
    <div className="animate-slide-up space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Market Statistics</h1>
        <p className="mt-1 text-sm text-slate-500">Aggregated pricing intelligence across all sources</p>
      </div>

      {/* KPI strip */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Total Products"     value={totalProducts.toLocaleString()} accent />
        <KpiCard label="Observations"       value={totalObs.toLocaleString()} />
        <KpiCard label="Sources Tracked"    value={String(stats.length)} />
        <KpiCard label="Global Avg Price"   value={globalAvg.toFixed(2)} sub={stats[0]?.currency} />
      </div>

      {/* Chart */}
      <div className="glass-card rounded-2xl p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Average Price by Source</h2>
            <p className="mt-0.5 text-xs text-slate-500">Comparison across all tracked marketplaces</p>
          </div>
          <div className="flex items-center gap-3">
            {stats.map((s, i) => (
              <span key={s.source} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="h-2 w-2 rounded-full" style={{ background: SOURCE_PALETTE[i % SOURCE_PALETTE.length] }} />
                {s.source.split('.')[0]}
              </span>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={stats} barSize={32} margin={{ left: -8, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" vertical={false} />
            <XAxis
              dataKey="source"
              stroke="transparent"
              tick={{ fontSize: 11, fill: '#475569' }}
              tickFormatter={v => v.split('.')[0]}
            />
            <YAxis
              stroke="transparent"
              tick={{ fontSize: 11, fill: '#475569' }}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.06)' }} />
            <Bar dataKey="avg_price" name="Avg Price" radius={[6, 6, 0, 0]}>
              {stats.map((_, idx) => (
                <Cell key={idx} fill={SOURCE_PALETTE[idx % SOURCE_PALETTE.length]} fillOpacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed table */}
      <div>
        <h2 className="mb-4 text-sm font-semibold text-slate-300">Detailed Breakdown</h2>
        <StatsTable stats={stats} />
      </div>
    </div>
  )
}
