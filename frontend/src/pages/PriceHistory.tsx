import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, TrendingDown, TrendingUp } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import Spinner from '../components/Spinner'

const DAYS_OPTIONS = [7, 14, 30, 60, 90]

export default function PriceHistory() {
  const { productId } = useParams<{ productId: string }>()
  const nav = useNavigate()

  const { data: product } = useQuery({
    queryKey: ['product', productId],
    queryFn: () => api.products.get(productId!),
    enabled: !!productId,
  })

  const { data: history, isLoading, refetch } = useQuery({
    queryKey: ['history', productId, 30],
    queryFn: () => api.products.history(productId!, 30),
    enabled: !!productId,
  })

  const first  = history?.[0]?.price
  const latest = history?.[history.length - 1]?.price
  const totalChange = first && latest ? ((latest - first) / first) * 100 : null

  return (
    <div>
      <button
        onClick={() => nav(-1)}
        className="mb-6 flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200"
      >
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      {product && (
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-100">{product.title}</h1>
          <div className="mt-1 flex items-center gap-3 text-sm text-slate-400">
            <span>{product.source}</span>
            <span>·</span>
            <a href={product.url} target="_blank" rel="noopener noreferrer"
               className="text-blue-400 hover:underline">
              View product ↗
            </a>
          </div>
        </div>
      )}

      {/* KPI row */}
      {history && history.length > 0 && (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          {[
            { label: 'Current price',  value: `${latest?.toFixed(2)} ${product?.currency}` },
            { label: 'Period high',    value: `${Math.max(...history.map(h => h.price)).toFixed(2)}` },
            { label: 'Period low',     value: `${Math.min(...history.map(h => h.price)).toFixed(2)}` },
            { label: 'Total change',   value: totalChange ? `${totalChange > 0 ? '+' : ''}${totalChange.toFixed(1)}%` : '–' },
          ].map(({ label, value }) => (
            <div key={label} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs text-slate-500">{label}</p>
              <p className={`mt-1 text-lg font-bold ${
                label === 'Total change' && totalChange !== null
                  ? totalChange < 0 ? 'text-green-400' : 'text-red-400'
                  : 'text-slate-100'
              }`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Day selector */}
      <div className="mb-4 flex items-center gap-2">
        {DAYS_OPTIONS.map(d => (
          <button
            key={d}
            onClick={() => refetch()}
            className="rounded border border-slate-700 px-3 py-1 text-sm text-slate-400 hover:border-slate-500 hover:text-slate-200"
          >
            {d}d
          </button>
        ))}
      </div>

      {isLoading && <Spinner label="Loading price history…" />}

      {history && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={history} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis
                dataKey="scraped_date"
                stroke="#475569"
                tick={{ fontSize: 11 }}
                tickFormatter={v => v.slice(5)}
              />
              <YAxis stroke="#475569" tick={{ fontSize: 11 }} width={60} />
              <Tooltip
                contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8 }}
                labelStyle={{ color: '#94a3b8' }}
                itemStyle={{ color: '#60a5fa' }}
              />
              {first && <ReferenceLine y={first} stroke="#334155" strokeDasharray="4 4" />}
              <Line
                type="monotone"
                dataKey="price"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, fill: '#3b82f6' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Change table */}
      {history && (
        <div className="mt-6 overflow-auto rounded-xl border border-slate-800 bg-slate-900">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-left text-xs text-slate-500">
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Price</th>
                <th className="px-4 py-3">Change</th>
                <th className="px-4 py-3">% Change</th>
              </tr>
            </thead>
            <tbody>
              {[...history].reverse().map((h, i) => (
                <tr key={i} className="border-b border-slate-800/50 hover:bg-slate-800/50">
                  <td className="px-4 py-2 text-slate-400">{h.scraped_date}</td>
                  <td className="px-4 py-2 font-mono text-slate-100">{h.price.toFixed(2)}</td>
                  <td className={`px-4 py-2 font-mono ${h.price_change_abs && h.price_change_abs < 0 ? 'text-green-400' : h.price_change_abs && h.price_change_abs > 0 ? 'text-red-400' : 'text-slate-500'}`}>
                    {h.price_change_abs != null
                      ? `${h.price_change_abs > 0 ? '+' : ''}${h.price_change_abs.toFixed(2)}`
                      : '–'}
                  </td>
                  <td className="px-4 py-2">
                    {h.price_change_pct != null ? (
                      <span className={`flex items-center gap-1 ${h.price_change_pct < 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {h.price_change_pct < 0 ? <TrendingDown className="h-3 w-3" /> : <TrendingUp className="h-3 w-3" />}
                        {h.price_change_pct > 0 ? '+' : ''}{h.price_change_pct.toFixed(2)}%
                      </span>
                    ) : '–'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
