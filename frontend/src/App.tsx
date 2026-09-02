import { BrowserRouter, Link, Route, Routes, useParams } from 'react-router-dom'
import VideoUpload from './components/VideoUpload'
import ProcessingView from './components/ProcessingView'
import ResultsPage from './pages/ResultsPage'

function JobRoute() {
  const { jobId } = useParams()
  if (!jobId) return null
  return <ProcessingView jobId={jobId} />
}

function ResultsRoute() {
  const { jobId } = useParams()
  if (!jobId) return null
  return <ResultsPage jobId={jobId} />
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-svh flex flex-col">
      <header className="px-6 py-5 flex items-center justify-between border-b border-[var(--border)]/60">
        <Link to="/" className="font-[family-name:var(--font-display)] text-[var(--text-h)] text-lg tracking-tight">
          Video AI Summarizer
        </Link>
        <span className="text-[var(--muted)] text-xs tracking-wide uppercase">
          Whisper · Scenes · LLM · Highlights
        </span>
      </header>
      <main className="flex-1 flex flex-col justify-center py-12">{children}</main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<VideoUpload />} />
          <Route path="/jobs/:jobId" element={<JobRoute />} />
          <Route path="/jobs/:jobId/results" element={<ResultsRoute />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  )
}
