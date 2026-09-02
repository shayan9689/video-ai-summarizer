import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle2, Cpu, Download } from 'lucide-react'
import { getFullResult, highlightReelUrl, type FullResult } from '../api/client'
import HighlightPlayer from '../components/HighlightPlayer'
import SceneTimeline from '../components/SceneTimeline'
import SummaryPanel from '../components/SummaryPanel'

export default function ResultsPage({ jobId }: { jobId: string }) {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [data, setData] = useState<FullResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void getFullResult(jobId)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))
  }, [jobId])

  function seek(seconds: number) {
    const el = videoRef.current
    if (!el) return
    el.currentTime = seconds
    void el.play()
  }

  if (error) {
    return (
      <p className="text-center text-[var(--danger)] px-6">
        {error} · <Link to="/">Start over</Link>
      </p>
    )
  }

  if (!data) {
    return <p className="text-center text-[var(--muted)] py-20">Loading neural results…</p>
  }

  if (data.status !== 'complete') {
    return (
      <p className="text-center text-[var(--muted)] py-20">
        Job is still {data.status}. <Link to={`/jobs/${jobId}`}>Back to synthesis</Link>
      </p>
    )
  }

  const scenes = data.scenes?.scenes ?? []
  const scored = data.highlights?.all_scored ?? data.highlights?.segments
  const name = data.video_metadata.filename

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="px-4 md:px-8 pb-12 max-w-[1100px] mx-auto w-full space-y-6"
    >
      <section className="glass rounded-[1.75rem] p-6 md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2 mb-2 text-[var(--cyan)]">
              <Cpu className="h-4 w-4" />
            </div>
            <h1 className="font-serif text-3xl md:text-4xl text-[var(--text-h)]">
              Synthesis Complete
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">{name}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-2 rounded-full border border-[var(--green)]/30 bg-[var(--green)]/10 px-3 py-1.5 text-[10px] tracking-[0.14em] uppercase text-[var(--green)]">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Complete
            </span>
            <a
              href={highlightReelUrl(jobId)}
              download
              className="flex items-center gap-2 rounded-full bg-gradient-to-r from-[var(--violet)] to-[var(--cyan)] px-4 py-2 text-sm font-medium text-black"
            >
              <Download className="h-4 w-4" />
              Download reel
            </a>
            <Link
              to="/"
              className="rounded-full border border-white/10 px-4 py-2 text-sm text-[var(--muted)] hover:text-[var(--text-h)]"
            >
              New upload
            </Link>
          </div>
        </div>

        <HighlightPlayer jobId={jobId} videoRef={videoRef} />
      </section>

      {data.summary && (
        <section className="glass rounded-[1.75rem] p-6 md:p-8">
          <SummaryPanel summary={data.summary} onSeek={seek} />
        </section>
      )}

      {scenes.length > 0 && (
        <section className="glass rounded-[1.75rem] p-6 md:p-8">
          <SceneTimeline scenes={scenes} scored={scored} onSeek={seek} />
        </section>
      )}
    </motion.div>
  )
}
