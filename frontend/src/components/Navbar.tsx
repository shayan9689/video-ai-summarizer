import { Link } from 'react-router-dom'
import { Bell, Box, Search, User } from 'lucide-react'

export default function Navbar() {
  return (
    <header className="relative z-20 flex items-center justify-between px-4 md:px-8 py-2.5">
      <Link to="/" className="flex items-center gap-3 group">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--violet)] to-[var(--cyan)] text-black shadow-[0_0_20px_rgba(168,85,247,0.4)]">
          <Box className="h-5 w-5" strokeWidth={2.2} />
        </span>
        <span className="tracking-[0.18em] text-sm font-semibold text-[var(--text-h)] group-hover:text-white transition-colors">
          NEURAFLUX
        </span>
      </Link>

      <nav className="hidden md:flex items-center gap-8 text-sm text-[var(--muted)]">
        <span className="hover:text-[var(--text-h)] cursor-default transition-colors">Projects</span>
        <span className="hover:text-[var(--text-h)] cursor-default transition-colors">Tools</span>
        <span className="hover:text-[var(--text-h)] cursor-default transition-colors">History</span>
      </nav>

      <div className="flex items-center gap-3 text-[var(--muted)]">
        <button type="button" className="p-2 rounded-full hover:bg-white/5 hover:text-[var(--text-h)] transition-colors" aria-label="Search">
          <Search className="h-4 w-4" />
        </button>
        <button type="button" className="p-2 rounded-full hover:bg-white/5 hover:text-[var(--text-h)] transition-colors" aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </button>
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--violet)]/30 border border-[var(--violet)]/40 text-[var(--text-h)]">
          <User className="h-4 w-4" />
        </span>
      </div>
    </header>
  )
}
