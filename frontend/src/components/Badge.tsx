const SOURCE_COLORS: Record<string, string> = {
  'books.toscrape.com': 'bg-violet-900 text-violet-300',
  'scrapeme.live':      'bg-yellow-900 text-yellow-300',
  'jumia.ma':           'bg-orange-900 text-orange-300',
  'ultrapc.ma':         'bg-cyan-900   text-cyan-300',
  'micromagma.ma':      'bg-green-900  text-green-300',
}

export default function Badge({ source }: { source: string }) {
  const cls = SOURCE_COLORS[source] ?? 'bg-slate-700 text-slate-300'
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>
      {source}
    </span>
  )
}
