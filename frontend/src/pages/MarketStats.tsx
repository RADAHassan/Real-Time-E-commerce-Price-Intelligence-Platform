import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import Spinner from '../components/Spinner'
import type { SourceStats } from '../types'

const PALETTE = ['#3b82f6', '#f59e0b', '#10b981', '#8b5cf6', '#ef4444']

function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-slate-100">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
    </div>
  )
}

function StatsRow({ s, i }: { s: SourceStats; i: number }) {
  const color = PALETTE[i % PALETTE.length]
  return (
    <tr className="border-b border-slate-800/50 hover:bg-slate-800/50">
      <td className="px-4 py-3">
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: color }} />
          {s.source}
        </span>
      </td>
      <td className="px-4 py-3 text-slate-400">{s.currency}</td>
      <td className="px-4 py-3 font-mono">{s.product_count}</td>
      <td className="px-4 py-3 font-mono">{s.avg_price.toFixed(2)}</td>
      <td className="px-4 py-3 font-mono">{s.median_price.toFixed(2)}</td>
      <td className="px-4 py-3 font-mono">{s.min_price.toFixed(2)}</td>
      <td className="px-4 py-3 font-mono">{s.max_price.toFixed(2)}</td>
      <td className="px-4 py-3 font-mono text-slate-400">{s.stddev_price?.toFixed(2) ?? '–'}</td>
    </tr>
  )
}

export default function MarketStats() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: api.stats,
  })

  if (isLoading) return <Spinner label="Loading market statistics…" />
  if (error || !stats) return <p className="text-red-400">Failed to load stats</p>

  const totalProducts = stats.reduce((s, r) => s + r.product_count, 0)
  const totalObs      = stats.reduce((s, r) => s + r.observation_count, 0)

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Market Statistics</h1>

      {/* KPI row */}
      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard label="Total products"    value={totalProducts.toLocaleString()} />
        <KpiCard label="Total observations" value={totalObs.toLocaleString()} />
        <KpiCard label="Sources tracked"   value={String(stats.length)} />
        <KpiCard label="Last updated"      value={stats[0]?.last_updated_date ?? '–'} />
      </div>

      {/* Avg price bar chart */}
      <div className="mb-8 rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-semibold text-slate-300">Average Price per Source</h2>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={stats} margin={{ left: 0, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="source" stroke="#475569" tick={{ fontSize: 11 }} />
            <YAxis stroke="#475569" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#94a3b8' }}
              formatter={(v: number) => [v.toFixed(2), 'avg price']}
            />
            <Bar dataKey="avg_price" radius={[4, 4, 0, 0]}>
              {stats.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detailed table */}
      <div className="overflow-auto rounded-xl border border-slate-800 bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800 text-left text-xs text-slate-500">
              {['Source','Currency','Products','Avg','Median','Min','Max','Std Dev'].map(h => (
                <th key={h} className="px-4 py-3">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {stats.map((s, i) => <StatsRow key={s.source} s={s} i={i} />)}
          </tbody>
        </table>
      </div>
    </div>
  )
}
