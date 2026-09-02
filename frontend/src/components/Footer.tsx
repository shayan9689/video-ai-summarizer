import { Globe } from 'lucide-react'

export default function Footer() {
  return (
    <footer className="relative z-10 flex flex-col sm:flex-row items-center justify-between gap-2 px-4 md:px-8 py-2.5 text-[10px] text-[var(--muted)] border-t border-[var(--border)]">
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
