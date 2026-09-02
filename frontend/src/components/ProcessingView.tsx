import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { connectJobSocket, getJobStatus, type JobStatusResponse } from '../api/client'

const STAGES = [
  { key: 'extracting_audio', label: 'Extracting audio' },
  { key: 'transcribing', label: 'Transcribing' },
  { key: 'analyzing_scenes', label: 'Analyzing scenes' },
  { key: 'summarizing', label: 'Summarizing' },
  { key: 'scoring_highlights', label: 'Scoring highlights' },
  { key: 'rendering', label: 'Rendering reel' },
  { key: 'complete', label: 'Complete' },
] as const

function stageIndex(status: string): number {
  const map: Record<string, number> = {
    uploaded: 0,
    extracting_audio: 0,
    transcribing: 1,
    transcribed: 1,
    segmented: 2,
    analyzing_scenes: 2,
    scenes_analyzed: 2,
    summarizing: 3,
    summarized: 3,
    scoring_highlights: 4,
    highlights_scored: 4,
    rendering: 5,
    complete: 6,
  }
  return map[status] ?? 0
}

export default function ProcessingView({ jobId }: { jobId: string }) {
  const navigate = useNavigate()
  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [socketError, setSocketError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    let ws: WebSocket | null = null

    const apply = (s: JobStatusResponse) => {
      if (cancelled) return
      setJob(s)
      if (s.status === 'complete') {
        navigate(`/jobs/${jobId}/results`, { replace: true })
      }
    }

    void getJobStatus(jobId)
      .then(apply)
      .catch(() => setSocketError('Could not load job status'))

    // Poll every 3s — Render free tier often drops WebSockets during long Whisper runs
    const poll = window.setInterval(() => {
      void getJobStatus(jobId)
        .then(apply)
        .catch(() => undefined)
    }, 3000)

    try {
      ws = connectJobSocket(jobId, apply)
      ws.onerror = () =>
        setSocketError('Live updates intermittent — status still refreshes automatically')
    } catch {
      setSocketError('WebSocket unavailable — using status polling')
    }

    return () => {
      cancelled = true
      window.clearInterval(poll)
      ws?.close()
    }
  }, [jobId, navigate])

  const idx = stageIndex(job?.status ?? 'uploaded')
  const failed = job?.status === 'failed'
  const transcribingHint =
    !failed && (job?.status === 'transcribing' || job?.progress_percent === 20)

  return (
    <section className="w-full max-w-lg mx-auto px-4">
      <motion.h2
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-2xl text-center mb-2"
      >
        Processing your video
      </motion.h2>
      <p className="text-center text-[var(--muted)] text-sm mb-10">
        {job?.progress_percent ?? 0}% · {job?.status ?? 'starting'}
      </p>

      <ol className="space-y-3">
        <AnimatePresence>
          {STAGES.map((stage, i) => {
            const done = i < idx || job?.status === 'complete'
            const active = i === idx && !failed && job?.status !== 'complete'
            return (
              <motion.li
                key={stage.key}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                className={`flex items-center gap-3 px-3 py-2 border-l-2 ${
                  active
                    ? 'border-[var(--accent)] text-[var(--text-h)]'
                    : done
                      ? 'border-[var(--accent-dim)] text-[var(--muted)]'
                      : 'border-[var(--border)] text-[var(--muted)]'
                }`}
              >
                <span className="w-5 text-xs tabular-nums">
                  {done ? '✓' : active ? '●' : String(i + 1).padStart(2, '0')}
                </span>
                <span className={active ? 'font-medium' : ''}>{stage.label}</span>
              </motion.li>
            )
          })}
        </AnimatePresence>
      </ol>

      <div className="mt-8 h-1 bg-[var(--border)] overflow-hidden">
        <motion.div
          className="h-full bg-[var(--accent)]"
          animate={{ width: `${job?.progress_percent ?? 0}%` }}
          transition={{ type: 'spring', stiffness: 80, damping: 20 }}
        />
      </div>

      {transcribingHint && (
        <p className="mt-6 text-center text-xs text-[var(--muted)]">
          First run can take several minutes while Whisper downloads/runs on the free server.
          Keep this tab open.
        </p>
      )}

      {failed && (
        <div className="mt-8 text-center">
          <p className="text-[var(--danger)] text-sm mb-4">
            {job?.error_message || 'Processing failed'}
          </p>
          <Link
            to="/"
            className="inline-block px-5 py-2 border border-[var(--border)] hover:border-[var(--accent)] transition-colors text-sm"
          >
            Try again
          </Link>
        </div>
      )}

      {socketError && !failed && (
        <p className="mt-6 text-center text-xs text-[var(--muted)]">{socketError}</p>
      )}
    </section>
  )
}
