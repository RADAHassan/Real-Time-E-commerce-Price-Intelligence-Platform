export default function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center gap-4 py-24 animate-fade-in">
      <div className="relative h-10 w-10">
        <div className="absolute inset-0 rounded-full border-2 border-indigo-500/20" />
        <div className="absolute inset-0 animate-spin rounded-full border-2 border-transparent border-t-indigo-500" />
      </div>
      <span className="text-sm text-slate-500">{label}</span>
    </div>
  )
}

export function SkeletonRow() {
  return (
    <tr className="border-b border-slate-800/40">
      {Array.from({ length: 7 }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3.5 animate-pulse rounded-md bg-slate-800" style={{ width: `${40 + (i * 13) % 50}%` }} />
        </td>
      ))}
    </tr>
  )
}
