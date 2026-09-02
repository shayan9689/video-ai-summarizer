import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { getFullResult, type FullResult } from '../api/client'
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
      <p className="text-center text-[var(--danger)]">
        {error} · <Link to="/">Start over</Link>
      </p>
    )
  }

  if (!data) {
    return <p className="text-center text-[var(--muted)]">Loading results…</p>
  }

  if (data.status !== 'complete') {
    return (
      <p className="text-center text-[var(--muted)]">
        Job is still {data.status}. <Link to={`/jobs/${jobId}`}>Back to progress</Link>
      </p>
    )
  }

  const scenes = data.scenes?.scenes ?? []
  const scored = data.highlights?.all_scored ?? data.highlights?.segments

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-5xl mx-auto px-4 space-y-12 pb-16"
    >
      <header className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <p className="text-[var(--accent)] text-xs tracking-[0.2em] uppercase mb-2">
            Results
          </p>
          <h2 className="text-3xl">{data.video_metadata.filename}</h2>
        </div>
        <Link
          to="/"
          className="text-sm text-[var(--muted)] hover:text-[var(--accent)] transition-colors"
        >
          New upload
        </Link>
      </header>

      <HighlightPlayer jobId={jobId} videoRef={videoRef} />

      {data.summary && <SummaryPanel summary={data.summary} onSeek={seek} />}

      {scenes.length > 0 && (
        <SceneTimeline scenes={scenes} scored={scored} onSeek={seek} />
      )}
    </motion.div>
  )
}
