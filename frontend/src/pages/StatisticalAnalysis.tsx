import { useQuery } from '@tanstack/react-query'
import clsx from 'clsx'
import { useState } from 'react'
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart,
  ResponsiveContainer, Scatter, ScatterChart,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api/client'
import { SourceDot } from '../components/Badge'
import Spinner from '../components/Spinner'
import type { ConfidenceInterval, DescriptiveStat, HypothesisTests, RegressionResult } from '../types'

// ── Color palette matching Badge.tsx ─────────────────────────────────────────
const SOURCE_COLORS: Record<string, string> = {
  'books.toscrape.com': '#6366f1',
  'scrapeme.live':      '#f59e0b',
  'jumia.ma':           '#fb923c',
  'ultrapc.ma':         '#22d3ee',
  'micromagma.ma':      '#34d399',
  'cdiscount.com':      '#f43f5e',
}
const FALLBACK = ['#6366f1', '#8b5cf6', '#a855f7', '#22d3ee', '#10b981', '#f59e0b', '#f43f5e']
const srcColor = (source: string, idx: number) => SOURCE_COLORS[source] ?? FALLBACK[idx % FALLBACK.length]

function fmtP(p: number): string {
  if (p < 0.0001) return '< 0.0001'
  return p.toFixed(4)
}

// ── Shared chart props ────────────────────────────────────────────────────────
const gridProps = { strokeDasharray: '3 3', stroke: 'rgba(99,102,241,0.08)', vertical: false } as const
const tooltipStyle = {
  contentStyle: { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, fontSize: 12 },
  labelStyle: { color: '#94a3b8' },
} as const

// ── Shared sub-components ─────────────────────────────────────────────────────
function SectionHeader({ title, badge }: { title: string; badge?: string }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <h2 className="text-sm font-semibold text-slate-200">{title}</h2>
      {badge && (
        <span className="rounded-md border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-xs font-semibold text-slate-500">
          {badge}
        </span>
      )}
    </div>
  )
}

function KpiCard({ label, value, sub, color = 'gradient' }: {
  label: string; value: string; sub?: string; color?: 'gradient' | 'emerald' | 'rose' | 'amber'
}) {
  const cls = color === 'emerald' ? 'text-emerald-400'
    : color === 'rose'   ? 'text-rose-400'
    : color === 'amber'  ? 'text-amber-400'
    : 'text-gradient'
  return (
    <div className="glass-card rounded-xl p-4">
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={clsx('text-2xl font-bold tracking-tight font-mono', cls)}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-600">{sub}</p>}
    </div>
  )
}

function TestCard({ title, subtitle, stat, statLabel, pValue, reject }: {
  title: string; subtitle: string; stat: number; statLabel: string; pValue: number; reject: boolean
}) {
  return (
    <div className="glass-card rounded-2xl p-6">
      <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">{title}</p>
      <p className="mt-0.5 text-xs text-slate-600">{subtitle}</p>
      <div className="mt-5 flex gap-8">
        <div>
          <p className="text-2xl font-bold font-mono text-gradient">{stat.toFixed(4)}</p>
          <p className="mt-0.5 text-xs text-slate-500">{statLabel}</p>
        </div>
        <div>
          <p className="text-2xl font-bold font-mono text-slate-200">{fmtP(pValue)}</p>
          <p className="mt-0.5 text-xs text-slate-500">p-value</p>
        </div>
      </div>
      <div className={clsx(
        'mt-4 rounded-lg border px-3 py-2 text-xs font-semibold',
        reject
          ? 'border-rose-500/20 bg-rose-500/8 text-rose-400'
          : 'border-slate-700 bg-slate-800/40 text-slate-500',
      )}>
        {reject ? '🔴 Reject H₀ — significant difference detected' : '🔵 Fail to reject H₀'}
      </div>
    </div>
  )
}

// ── Tab 1: Descriptive ────────────────────────────────────────────────────────
function BoxPlotTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0]?.payload
  if (!d) return null
  return (
    <div className="rounded-xl border border-slate-700/60 bg-slate-900/95 px-4 py-3 shadow-xl">
      <p className="mb-2 text-xs font-semibold text-slate-400">{label}</p>
      {[['Max', d.max, 'text-rose-400'], ['Q75', d.q75, 'text-slate-300'], ['Median', d.median, 'text-gradient font-bold'],
        ['Q25', d.q25, 'text-slate-300'], ['Min', d.min, 'text-emerald-400']].map(([name, val, cls]) => (
        <p key={name as string} className="flex justify-between gap-6 text-xs">
          <span className="text-slate-500">{name}</span>
          <span className={`font-mono font-semibold ${cls}`}>{(val as number).toFixed(2)}</span>
        </p>
      ))}
    </div>
  )
}

function DescriptiveTab({ data, histData }: {
  data: DescriptiveStat[]
  histData: { sources: string[]; bins: any[] } | undefined
}) {
  const fmt = (key: string, val: unknown): string => {
    if (key === 'source') return ''
    if (key === 'n') return (val as number)?.toLocaleString() ?? '—'
    if (val == null) return '—'
    if (key === 'cv') return `${(val as number).toFixed(1)}%`
    return typeof val === 'number' ? val.toFixed(2) : String(val)
  }

  const cols = [
    { key: 'source',   label: 'Source',  grad: false, green: false, rose: false },
    { key: 'n',        label: 'n',       grad: false, green: false, rose: false },
    { key: 'mean',     label: 'Mean',    grad: true,  green: false, rose: false },
    { key: 'median',   label: 'Median',  grad: false, green: false, rose: false },
    { key: 'std',      label: 'Std Dev', grad: false, green: false, rose: false },
    { key: 'cv',       label: 'CV %',    grad: false, green: false, rose: false },
    { key: 'min',      label: 'Min',     grad: false, green: true,  rose: false },
    { key: 'q25',      label: 'Q25',     grad: false, green: false, rose: false },
    { key: 'q75',      label: 'Q75',     grad: false, green: false, rose: false },
    { key: 'max',      label: 'Max',     grad: false, green: false, rose: true  },
    { key: 'skew',     label: 'Skew',    grad: false, green: false, rose: false },
    { key: 'kurtosis', label: 'Kurt',    grad: false, green: false, rose: false },
  ]

  // Box plot data (stacked bars on log10 scale, one column per source)
  const safeLog = (v: number) => Math.log10(Math.max(v, 0.01))
  const boxData = data.map((d, i) => {
    const logMin = safeLog(d.min)
    const logQ25 = safeLog(d.q25)
    const logQ75 = safeLog(d.q75)
    const logMax = safeLog(d.max)
    return {
      source: d.source.split('.')[0],
      fill: srcColor(d.source, i),
      offset:      logMin,
      whisker_lo:  Math.max(logQ25 - logMin, 0),
      box_body:    Math.max(logQ75 - logQ25, 0),
      whisker_hi:  Math.max(logMax - logQ75, 0),
      min: d.min, q25: d.q25, median: d.median, q75: d.q75, max: d.max,
    }
  })

  const logTickFmt = (v: number) => {
    const val = Math.pow(10, v)
    if (val >= 10_000) return `${(val / 1000).toFixed(0)}k`
    if (val >= 1_000)  return `${(val / 1000).toFixed(1)}k`
    if (val >= 10)     return val.toFixed(0)
    return val.toFixed(1)
  }

  // CV chart (vertical, sorted desc)
  const cvData = [...data].sort((a, b) => b.cv - a.cv)

  return (
    <div className="space-y-8">
      {/* Stats table */}
      <div>
        <SectionHeader title="Descriptive Statistics" badge="per source · all observations" />
        <div className="overflow-hidden rounded-2xl border border-slate-800/60">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800/60 bg-slate-900/60">
                  {cols.map(c => (
                    <th key={c.key} className="whitespace-nowrap px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                      {c.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, i) => (
                  <tr key={row.source} className={clsx(
                    'border-b border-slate-800/30',
                    i % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20',
                  )}>
                    {cols.map(c => (
                      <td key={c.key} className="px-4 py-3.5">
                        {c.key === 'source' ? (
                          <span className="flex items-center gap-2">
                            <SourceDot source={row.source} />
                            <span className="text-slate-200 font-medium">{row.source}</span>
                          </span>
                        ) : (
                          <span className={clsx(
                            'font-mono text-sm',
                            c.grad  && 'text-gradient font-bold',
                            c.green && 'text-emerald-400 font-semibold',
                            c.rose  && 'text-rose-400 font-semibold',
                            !c.grad && !c.green && !c.rose && 'text-slate-300',
                          )}>
                            {fmt(c.key, (row as unknown as Record<string, unknown>)[c.key])}
                          </span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Box plots */}
      <div className="glass-card rounded-2xl p-6">
        <SectionHeader title="Box Plots" badge="all sources · log scale" />
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={boxData} margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" vertical={false} />
            <XAxis dataKey="source" stroke="transparent" tick={{ fontSize: 11, fill: '#475569' }} tickLine={false} />
            <YAxis stroke="transparent" tick={{ fontSize: 11, fill: '#475569' }} tickLine={false}
                   tickFormatter={logTickFmt} label={{ value: 'Price (log scale)', angle: -90, position: 'insideLeft', fill: '#475569', fontSize: 10, offset: 8 }} />
            <Tooltip content={<BoxPlotTooltip />} cursor={{ fill: 'rgba(99,102,241,0.04)' }} />
            {/* Transparent offset to baseline (min) */}
            <Bar dataKey="offset" stackId="box" fill="transparent" legendType="none" />
            {/* Lower whisker: min → Q25 */}
            <Bar dataKey="whisker_lo" stackId="box" maxBarSize={10} legendType="none">
              {boxData.map((e, i) => <Cell key={i} fill={e.fill} fillOpacity={0.3} />)}
            </Bar>
            {/* Box body: Q25 → Q75 */}
            <Bar dataKey="box_body" stackId="box" maxBarSize={36} radius={[3, 3, 0, 0]} legendType="none">
              {boxData.map((e, i) => <Cell key={i} fill={e.fill} fillOpacity={0.85} />)}
            </Bar>
            {/* Upper whisker: Q75 → max */}
            <Bar dataKey="whisker_hi" stackId="box" maxBarSize={10} legendType="none">
              {boxData.map((e, i) => <Cell key={i} fill={e.fill} fillOpacity={0.3} />)}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Histogram + CV side by side */}
      <div className="grid grid-cols-2 gap-6">
        {/* Histogram */}
        <div className="glass-card rounded-2xl p-6">
          <SectionHeader title="Distribution" badge="log scale · stacked by source" />
          {histData && histData.bins.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={histData.bins} barSize={10} margin={{ left: -8, right: 8, top: 4, bottom: 16 }} barGap={0} barCategoryGap={0}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" vertical={false} />
                <XAxis dataKey="price_label" stroke="transparent"
                       tick={{ fontSize: 9, fill: '#475569' }} tickLine={false}
                       interval={4}
                       label={{ value: 'Price (log)', position: 'insideBottom', offset: -8, fill: '#475569', fontSize: 10 }} />
                <YAxis stroke="transparent" tick={{ fontSize: 10, fill: '#475569' }} tickLine={false} width={36} />
                <Tooltip
                  contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, fontSize: 11 }}
                  labelStyle={{ color: '#94a3b8' }}
                  labelFormatter={(l) => `~${l}`}
                />
                {histData.sources.map((src, i) => (
                  <Bar key={src} dataKey={src} stackId="h" fill={srcColor(src, i)} fillOpacity={0.8} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-center text-xs text-slate-600 py-8">Loading…</p>
          )}
          {histData && (
            <div className="mt-3 flex flex-wrap gap-3">
              {histData.sources.map((src, i) => (
                <span key={src} className="flex items-center gap-1.5 text-xs text-slate-500">
                  <span className="h-2 w-2 rounded-sm" style={{ background: srcColor(src, i) }} />
                  {src.split('.')[0]}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* CV chart (vertical, sorted desc) */}
        <div className="glass-card rounded-2xl p-6">
          <SectionHeader title="Coefficient of Variation" badge="volatility %" />
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={cvData} margin={{ left: -8, right: 8, top: 8, bottom: 4 }} barSize={32}>
              <CartesianGrid {...gridProps} />
              <XAxis dataKey="source" stroke="transparent" tick={{ fontSize: 10, fill: '#475569' }} tickLine={false}
                     tickFormatter={(s: string) => s.split('.')[0]} />
              <YAxis stroke="transparent" tick={{ fontSize: 10, fill: '#475569' }} tickLine={false}
                     tickFormatter={(v: number) => `${v}%`} width={38} />
              <Tooltip {...tooltipStyle}
                formatter={(v: number) => [`${v.toFixed(1)}%`, 'CV']}
                labelFormatter={(s: string) => s} />
              <Bar dataKey="cv" radius={[6, 6, 0, 0]}>
                {cvData.map((entry, i) => (
                  <Cell key={i} fill={srcColor(entry.source, i)} fillOpacity={0.85} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

// ── Tab 2: Hypothesis Tests ───────────────────────────────────────────────────
function CIForest({ data }: { data: ConfidenceInterval[] }) {
  const maxRel = Math.max(...data.map(r => r.rel_width), 0.001)
  return (
    <div className="glass-card rounded-2xl p-6 space-y-4">
      <p className="text-xs text-slate-600">
        Bar width = CI width as % of mean — currency-independent measure of estimation precision.
        Narrower = tighter estimate.
      </p>
      {data.map((r, i) => {
        const barPct = (r.rel_width / maxRel) * 100
        const col = srcColor(r.source, i)
        return (
          <div key={r.source} className="flex items-center gap-4">
            <div className="w-36 flex items-center gap-2 flex-shrink-0">
              <SourceDot source={r.source} />
              <span className="text-xs text-slate-300 truncate">{r.source.split('.')[0]}</span>
            </div>
            <div className="flex-1 h-4 relative">
              <div className="absolute inset-y-1 left-0 right-0 rounded-sm bg-slate-800/50" />
              <div
                className="absolute inset-y-0.5 left-0 rounded-sm transition-all"
                style={{ width: `${barPct}%`, background: `${col}28`, border: `1px solid ${col}55` }}
              />
            </div>
            <div className="w-52 font-mono text-xs flex-shrink-0 flex items-center gap-1.5 text-slate-500">
              <span className="text-slate-400">{r.ci_lower.toFixed(1)}</span>
              <span>–</span>
              <span className="text-gradient font-bold text-sm">{r.mean.toFixed(1)}</span>
              <span>–</span>
              <span className="text-slate-400">{r.ci_upper.toFixed(1)}</span>
            </div>
            <div className="w-24 font-mono text-xs text-slate-600 flex-shrink-0 text-right">
              n={r.n.toLocaleString()}
            </div>
          </div>
        )
      })}
    </div>
  )
}

function TestsTab({ data }: { data: HypothesisTests }) {
  const { normality, anova, kruskal, pairwise, confidence_intervals } = data
  return (
    <div className="space-y-8">
      <div className="grid grid-cols-2 gap-6">
        <TestCard title="One-Way ANOVA" subtitle="H₀: all group means are equal"
          stat={anova.f_stat} statLabel="F-statistic"
          pValue={anova.p_value} reject={anova.reject} />
        <TestCard title="Kruskal-Wallis" subtitle="Non-parametric · H₀: all distributions equal"
          stat={kruskal.h_stat} statLabel="H-statistic"
          pValue={kruskal.p_value} reject={kruskal.reject} />
      </div>

      <div>
        <SectionHeader title="Shapiro-Wilk Normality" badge="H₀: data is normally distributed" />
        <div className="overflow-hidden rounded-2xl border border-slate-800/60">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/60 bg-slate-900/60">
                {['Source', 'n', 'W statistic', 'p-value', 'Normal?'].map(h => (
                  <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {normality.map((r, i) => (
                <tr key={r.source} className={clsx(
                  'border-b border-slate-800/30',
                  i % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20',
                )}>
                  <td className="px-4 py-3.5">
                    <span className="flex items-center gap-2">
                      <SourceDot source={r.source} />
                      <span className="text-slate-200">{r.source}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-slate-400">{r.n.toLocaleString()}</td>
                  <td className="px-4 py-3.5 font-mono text-gradient font-bold">{r.w_stat.toFixed(4)}</td>
                  <td className="px-4 py-3.5 font-mono text-slate-300">{fmtP(r.p_value)}</td>
                  <td className="px-4 py-3.5">
                    <span className={clsx(
                      'rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                      r.is_normal
                        ? 'border-emerald-500/25 bg-emerald-500/8 text-emerald-400'
                        : 'border-rose-500/25 bg-rose-500/8 text-rose-400',
                    )}>
                      {r.is_normal ? '✓ Normal' : '✗ Non-normal'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <SectionHeader title="Mann-Whitney U — Pairwise" badge="two-sided · sorted by p-value" />
        <div className="overflow-hidden rounded-2xl border border-slate-800/60">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-800/60 bg-slate-900/60">
                {['Source A', 'Source B', 'U statistic', 'p-value', 'Effect r', 'Sig?'].map(h => (
                  <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pairwise.map((r, i) => (
                <tr key={`${r.source_a}_${r.source_b}`} className={clsx(
                  'border-b border-slate-800/30',
                  i % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20',
                )}>
                  <td className="px-4 py-3.5">
                    <span className="flex items-center gap-1.5">
                      <SourceDot source={r.source_a} />
                      <span className="text-xs text-slate-300">{r.source_a.split('.')[0]}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3.5">
                    <span className="flex items-center gap-1.5">
                      <SourceDot source={r.source_b} />
                      <span className="text-xs text-slate-300">{r.source_b.split('.')[0]}</span>
                    </span>
                  </td>
                  <td className="px-4 py-3.5 font-mono text-slate-400">
                    {r.u_stat.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </td>
                  <td className="px-4 py-3.5 font-mono font-bold text-gradient">{fmtP(r.p_value)}</td>
                  <td className="px-4 py-3.5 font-mono text-slate-400">{r.effect_r.toFixed(4)}</td>
                  <td className="px-4 py-3.5">
                    <span className={clsx(
                      'rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                      r.significant
                        ? 'border-emerald-500/25 bg-emerald-500/8 text-emerald-400'
                        : 'border-slate-700 bg-slate-800/40 text-slate-500',
                    )}>
                      {r.significant ? '✓' : '✗'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <SectionHeader title="95% Confidence Intervals — Mean Price" badge="relative CI width · forest plot" />
        <CIForest data={confidence_intervals} />
      </div>
    </div>
  )
}

// ── Tab 3: Regression ─────────────────────────────────────────────────────────
function RegressionTab({ data }: { data: RegressionResult }) {
  const { slope, intercept, r2, p_value, scatter, per_source } = data
  const isSignificant = p_value < 0.05

  const sources = [...new Set(scatter.map(p => p.source))]
  const bySource = sources.reduce((acc, src) => {
    acc[src] = scatter
      .filter(p => p.source === src)
      .map(p => ({ x: p.rating, y: p.price }))
    return acc
  }, {} as Record<string, { x: number; y: number }[]>)

  return (
    <div className="space-y-8">
      <div className="grid grid-cols-4 gap-4">
        <KpiCard label="Slope β₁" value={slope >= 0 ? `+${slope}` : String(slope)}
          sub="price change per ⭐" color={slope >= 0 ? 'emerald' : 'rose'} />
        <KpiCard label="Intercept β₀" value={intercept.toFixed(2)} />
        <KpiCard label="R² fit quality" value={r2.toFixed(4)}
          sub={r2 > 0.3 ? 'strong fit' : r2 > 0.1 ? 'moderate fit' : 'weak fit'}
          color={r2 > 0.3 ? 'emerald' : 'amber'} />
        <KpiCard label="p-value" value={fmtP(p_value)}
          sub={isSignificant ? 'significant at α = 0.05' : 'not significant'}
          color={isSignificant ? 'emerald' : 'rose'} />
      </div>

      <div className="glass-card rounded-2xl p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-slate-200">Price vs Rating — Scatter Plot</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              Sample of {scatter.length.toLocaleString()} observations · colored by source
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            {sources.map((src, i) => (
              <span key={src} className="flex items-center gap-1.5 text-xs text-slate-500">
                <span className="h-2 w-2 rounded-full" style={{ background: srcColor(src, i) }} />
                {src.split('.')[0]}
              </span>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart margin={{ left: -8, right: 8, top: 8, bottom: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(99,102,241,0.08)" />
            <XAxis dataKey="x" type="number" name="Rating" domain={[0, 5.5]}
              stroke="transparent" tick={{ fontSize: 11, fill: '#475569' }} tickLine={false}
              label={{ value: 'Rating (⭐)', position: 'insideBottom', offset: -10, fill: '#475569', fontSize: 11 }} />
            <YAxis dataKey="y" type="number" name="Price"
              stroke="transparent" tick={{ fontSize: 11, fill: '#475569' }} tickLine={false} width={60} />
            <Tooltip
              cursor={{ strokeDasharray: '3 3', stroke: '#334155' }}
              contentStyle={{ background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, fontSize: 12 }}
              formatter={(val: number, name: string) => [val.toFixed(2), name === 'x' ? 'Rating' : 'Price']}
            />
            {sources.map((src, i) => (
              <Scatter key={src} name={src} data={bySource[src] ?? []}
                fill={srcColor(src, i)} opacity={0.4} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {per_source.length > 0 && (
        <div>
          <SectionHeader title="Regression per Source" badge="price ~ rating" />
          <div className="overflow-hidden rounded-2xl border border-slate-800/60">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-800/60 bg-slate-900/60">
                  {['Source', 'n', 'Slope β₁', 'Intercept β₀', 'R', 'R²', 'p-value', 'Sig?'].map(h => (
                    <th key={h} className="px-4 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {per_source.map((r, i) => (
                  <tr key={r.source} className={clsx(
                    'border-b border-slate-800/30',
                    i % 2 === 0 ? 'bg-transparent' : 'bg-slate-900/20',
                  )}>
                    <td className="px-4 py-3.5">
                      <span className="flex items-center gap-2">
                        <SourceDot source={r.source} />
                        <span className="text-slate-200">{r.source}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-400">{r.n.toLocaleString()}</td>
                    <td className={clsx(
                      'px-4 py-3.5 font-mono font-bold',
                      r.slope >= 0 ? 'text-emerald-400' : 'text-rose-400',
                    )}>
                      {r.slope >= 0 ? '+' : ''}{r.slope.toFixed(4)}
                    </td>
                    <td className="px-4 py-3.5 font-mono text-slate-400">{r.intercept.toFixed(2)}</td>
                    <td className="px-4 py-3.5 font-mono text-slate-400">{r.r.toFixed(4)}</td>
                    <td className="px-4 py-3.5 font-mono text-gradient font-bold">{r.r2.toFixed(4)}</td>
                    <td className="px-4 py-3.5 font-mono text-slate-400">{fmtP(r.p_value)}</td>
                    <td className="px-4 py-3.5">
                      <span className={clsx(
                        'rounded-full border px-2.5 py-0.5 text-xs font-semibold',
                        r.significant
                          ? 'border-emerald-500/25 bg-emerald-500/8 text-emerald-400'
                          : 'border-slate-700 bg-slate-800/40 text-slate-500',
                      )}>
                        {r.significant ? '✓' : '✗'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main export ───────────────────────────────────────────────────────────────
type TabId = 'descriptive' | 'tests' | 'regression'
const TABS: { id: TabId; label: string }[] = [
  { id: 'descriptive', label: '📊  Descriptive' },
  { id: 'tests',       label: '🧪  Hypothesis Tests' },
  { id: 'regression',  label: '📐  Regression' },
]

export default function StatisticalAnalysis() {
  const [tab, setTab] = useState<TabId>('descriptive')

  const { data: desc, isLoading: descLoading, error: descErr } = useQuery({
    queryKey: ['analysis', 'descriptive'],
    queryFn: api.analysis.descriptive,
    staleTime: 10 * 60 * 1000,
  })

  const { data: tests, isLoading: testsLoading } = useQuery({
    queryKey: ['analysis', 'tests'],
    queryFn: api.analysis.tests,
    staleTime: 10 * 60 * 1000,
    enabled: tab === 'tests',
  })

  const { data: reg, isLoading: regLoading } = useQuery({
    queryKey: ['analysis', 'regression'],
    queryFn: api.analysis.regression,
    staleTime: 10 * 60 * 1000,
    enabled: tab === 'regression',
  })

  const { data: hist } = useQuery({
    queryKey: ['analysis', 'histogram'],
    queryFn: api.analysis.histogram,
    staleTime: 10 * 60 * 1000,
    enabled: tab === 'descriptive',
  })

  const isLoading =
    (tab === 'descriptive' && descLoading) ||
    (tab === 'tests'       && testsLoading) ||
    (tab === 'regression'  && regLoading)

  return (
    <div className="animate-slide-up space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Statistical Analysis</h1>
        <p className="mt-1 text-sm text-slate-500">
          Descriptive statistics · Hypothesis tests · Linear regression · 67 k products
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex items-center gap-1 rounded-xl border border-slate-800/60 bg-slate-900/40 p-1">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={clsx(
              'flex-1 rounded-lg py-2 text-sm font-medium transition',
              tab === t.id
                ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/20'
                : 'text-slate-500 hover:text-slate-300',
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {tab === 'descriptive' && descErr && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-8 text-center text-rose-400 text-sm">
          Failed to load analysis — {String(descErr)}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <Spinner label={
          tab === 'tests'      ? 'Running hypothesis tests…' :
          tab === 'regression' ? 'Computing regression…' :
          'Loading statistics…'
        } />
      )}

      {/* Content */}
      {!isLoading && (
        <>
          {tab === 'descriptive' && desc && desc.length > 0 && <DescriptiveTab data={desc} histData={hist} />}
          {tab === 'tests'       && tests && 'anova' in tests && <TestsTab data={tests} />}
          {tab === 'regression'  && reg   && reg.n > 0        && <RegressionTab data={reg} />}
          {tab === 'regression'  && reg   && reg.n === 0      && (
            <div className="rounded-2xl border border-slate-800/60 p-12 text-center">
              <p className="text-slate-500">Not enough rated products for regression analysis.</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
