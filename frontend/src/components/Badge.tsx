const SOURCE_STYLES: Record<string, { dot: string; text: string; bg: string }> = {
  'books.toscrape.com': { dot: 'bg-violet-400',  text: 'text-violet-300',  bg: 'bg-violet-500/10 border-violet-500/20' },
  'scrapeme.live':      { dot: 'bg-amber-400',   text: 'text-amber-300',   bg: 'bg-amber-500/10  border-amber-500/20'  },
  'jumia.ma':           { dot: 'bg-orange-400',  text: 'text-orange-300',  bg: 'bg-orange-500/10 border-orange-500/20' },
  'ultrapc.ma':         { dot: 'bg-cyan-400',    text: 'text-cyan-300',    bg: 'bg-cyan-500/10   border-cyan-500/20'   },
  'micromagma.ma':      { dot: 'bg-emerald-400', text: 'text-emerald-300', bg: 'bg-emerald-500/10 border-emerald-500/20' },
  'cdiscount.com':      { dot: 'bg-rose-400',    text: 'text-rose-300',    bg: 'bg-rose-500/10   border-rose-500/20'   },
}

const DEFAULT_STYLE = { dot: 'bg-slate-400', text: 'text-slate-300', bg: 'bg-slate-500/10 border-slate-500/20' }

export default function Badge({ source }: { source: string }) {
  const s = SOURCE_STYLES[source] ?? DEFAULT_STYLE
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
      {source}
    </span>
  )
}

export function SourceDot({ source }: { source: string }) {
  const s = SOURCE_STYLES[source] ?? DEFAULT_STYLE
  return <span className={`stat-dot ${s.dot}`} />
}
