import { Globe } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="relative z-10 flex flex-col sm:flex-row items-center justify-between gap-3 px-6 md:px-10 py-5 text-xs text-[var(--muted)] border-t border-[var(--border)]">
      <div className="flex items-center gap-2">
        <Globe className="h-3.5 w-3.5 text-[var(--cyan)]" />
        <span>AI Processing Core v2.4.0</span>
      </div>
      <div className="flex items-center gap-5">
        <span className="hover:text-[var(--text-h)] cursor-default">Documentation</span>
        <span className="hover:text-[var(--text-h)] cursor-default">Support</span>
        <span className="hover:text-[var(--text-h)] cursor-default">Privacy</span>
      </div>
    </footer>
  )
}
