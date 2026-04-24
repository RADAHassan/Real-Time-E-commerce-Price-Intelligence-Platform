import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom'
import Alerts from './pages/Alerts'
import LivePrices from './pages/LivePrices'
import MarketStats from './pages/MarketStats'
import PriceHistory from './pages/PriceHistory'

const NAV = [
  { to: '/',        label: 'Live Prices' },
  { to: '/stats',   label: 'Market Stats' },
  { to: '/alerts',  label: 'Alerts' },
]

function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-8 px-6 py-3">
        <span className="flex items-center gap-2 font-bold text-blue-400">
          <span className="text-xl">📊</span>
          Price Intelligence
        </span>
        <div className="flex gap-1">
          {NAV.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950">
        <Navbar />
        <main className="mx-auto max-w-7xl px-6 py-8">
          <Routes>
            <Route path="/"                       element={<LivePrices />} />
            <Route path="/stats"                  element={<MarketStats />} />
            <Route path="/alerts"                 element={<Alerts />} />
            <Route path="/history/:productId"     element={<PriceHistory />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
