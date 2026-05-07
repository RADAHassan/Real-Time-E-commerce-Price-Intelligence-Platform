import { Activity, Atom, BarChart3, Bell, TrendingDown, Zap } from 'lucide-react'
import { NavLink, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import Alerts from './pages/Alerts'
import LivePrices from './pages/LivePrices'
import MarketStats from './pages/MarketStats'
import PriceHistory from './pages/PriceHistory'
import StatisticalAnalysis from './pages/StatisticalAnalysis'

const NAV = [
  { to: '/',        label: 'Live Prices',    icon: Activity,      end: true  },
  { to: '/stats',   label: 'Market Stats',   icon: BarChart3,     end: false },
  { to: '/analysis', label: 'Analysis',       icon: Atom,          end: false },
  { to: '/alerts',  label: 'Price Alerts',   icon: TrendingDown,  end: false },
]

function Logo() {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-brand shadow-glow-sm">
        <Zap className="h-4 w-4 text-white" strokeWidth={2.5} />
      </div>
      <span className="text-sm font-bold tracking-tight text-gradient">
        Price Intelligence
      </span>
    </div>
  )
}

function Navbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-indigo-500/10 bg-slate-950/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-3">
        <Logo />

        <nav className="flex items-center gap-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => `nav-link flex items-center gap-2 ${isActive ? 'active' : ''}`}
            >
              <Icon className="h-3.5 w-3.5" strokeWidth={2} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded-full border border-indigo-500/15 bg-indigo-500/8 px-3 py-1.5">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            <span className="text-xs font-medium text-slate-400">Live</span>
          </div>
          <button className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 text-slate-500 transition hover:border-indigo-500/30 hover:text-slate-300">
            <Bell className="h-4 w-4" />
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-brand text-xs font-bold text-white shadow-glow-sm">
            HR
          </div>
        </div>
      </div>
    </header>
  )
}

export default function App() {
  return (
    <Router>
      <div className="min-h-screen" style={{ background: '#020617' }}>
        <Navbar />
        <main className="mx-auto max-w-7xl px-6 py-8 animate-fade-in">
          <Routes>
            <Route path="/"                   element={<LivePrices />} />
            <Route path="/stats"              element={<MarketStats />} />
            <Route path="/alerts"             element={<Alerts />} />
            <Route path="/analysis"            element={<StatisticalAnalysis />} />
            <Route path="/history/:productId" element={<PriceHistory />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}
