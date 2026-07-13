import { NavLink, Route, Routes } from 'react-router-dom'
import Experiments from './pages/Experiments.jsx'
import History from './pages/History.jsx'
import Settings from './pages/Settings.jsx'

export default function App() {
  return (
    <div className="app">
      <nav className="topnav">
        <NavLink to="/" className="brand">
          <span className="brand-mark">PL</span>
          <span className="brand-name">PromptLab</span>
        </NavLink>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            Playground
          </NavLink>
          <NavLink to="/history" className={({ isActive }) => (isActive ? 'active' : '')}>
            History
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => (isActive ? 'active' : '')}>
            Settings
          </NavLink>
        </div>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<Experiments />} />
          <Route path="/history" element={<History />} />
          <Route path="/experiments/:id" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}
