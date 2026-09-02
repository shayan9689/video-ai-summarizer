import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Check,
  Cpu,
  Eye,
  Film,
  Settings2,
  Sparkles,
  StopCircle,
  Waves,
} from 'lucide-react'
import {
  connectJobSocket,
  getFullResult,
  getJobStatus,
  originalVideoUrl,
  thumbnailUrl,
  type JobStatusResponse,
  type Scene,
} from '../api/client'

const PIPELINE = [
  {
    key: 'extracting_audio',
    label: 'Extracting Audio',
    detail: 'WAV isolation complete.',
  },
  {
    key: 'transcribing',
    label: 'Transcribing',
    detail: 'Speech → text · neural ASR',
  },
  {
    key: 'analyzing_scenes',
    label: 'Visual Synthesis',
    detail: 'Scenes · highlights · render',
  },
] as const

function stageBucket(status: string): number {
  const map: Record<string, number> = {
    uploaded: 0,
    extracting_audio: 0,
    transcribing: 1,
    transcribed: 1,
    segmented: 1,
    analyzing_scenes: 2,
    scenes_analyzed: 2,
    summarizing: 2,
    summarized: 2,
    scoring_highlights: 2,
    highlights_scored: 2,
    rendering: 2,
    complete: 3,
  }
  return map[status] ?? 0
}

function formatTimecode(seconds?: number | null): string {
  const s = Math.max(0, Math.floor(seconds || 0))
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}:00`
}

function formatShort(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function ProcessingView({ jobId }: { jobId: string }) {
  const navigate = useNavigate()
  const [job, setJob] = useState<JobStatusResponse | null>(null)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [liveQuote, setLiveQuote] = useState(
    '…neural core is aligning audio, transcript, and scenes…',
  )

  useEffect(() => {
    let cancelled = false
    let ws: WebSocket | null = null

    const apply = (s: JobStatusResponse) => {
      if (cancelled) return
      setJob(s)
      if (s.status === 'complete') navigate(`/jobs/${jobId}/results`, { replace: true })
    }

    void getJobStatus(jobId).then(apply).catch(() => undefined)

    const poll = window.setInterval(() => {
      void getJobStatus(jobId).then(apply).catch(() => undefined)
      void getFullResult(jobId)
        .then((r) => {
          if (cancelled) return
          const sc = r.scenes?.scenes ?? []
          if (sc.length) setScenes(sc)
          const quote = r.summary?.notable_quotes?.[0]?.text
          const overview = r.summary?.overview
          if (quote) setLiveQuote(`"${quote}"`)
          else if (overview)
            setLiveQuote(overview.slice(0, 120) + (overview.length > 120 ? '…' : ''))
        })
        .catch(() => undefined)
    }, 3000)

    try {
      ws = connectJobSocket(jobId, apply)
    } catch {
      /* polling */
    }

    return () => {
      cancelled = true
      window.clearInterval(poll)
      ws?.close()
    }
  }, [jobId, navigate])

  const pct = job?.progress_percent ?? 0
  const status = job?.status ?? 'uploaded'
  const bucket = stageBucket(status)
  const failed = status === 'failed'
  const projectName = job?.filename?.replace(/\.[^.]+$/, '') || 'Neon_Drift_V2'

  const checklist = useMemo(
    () => [
      { label: 'Audio', done: bucket > 0 || pct >= 15 },
      { label: 'Transcribe', done: bucket > 1, active: bucket === 1 },
      {
        label: 'Scenes',
        done: bucket > 2 || status === 'complete',
        active: bucket === 2 && status !== 'complete',
      },
      {
        label: 'Summary',
        done: ['summarized', 'scoring_highlights', 'highlights_scored', 'rendering', 'complete'].includes(
          status,
        ),
      },
      {
        label: 'Highlights',
        done: ['highlights_scored', 'rendering', 'complete'].includes(status),
      },
      { label: 'Render', done: status === 'complete' },
    ],
    [bucket, pct, status],
  )

  const visionCards = [...scenes.slice(0, 2)]
  while (visionCards.length < 2) {
    visionCards.push({
      scene_index: visionCards.length,
      start: visionCards.length * 12,
      end: visionCards.length * 12 + 8,
      motion_score: 0.5,
      thumbnail_path: null,
    })
  }

  return (
    <div className="px-3 md:px-6 max-w-[1200px] mx-auto w-full">
      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-3 h-[calc(100svh-7.5rem)] min-h-0">
        <section className="glass rounded-2xl p-3.5 md:p-4 flex flex-col min-h-0 overflow-hidden">
          <div className="flex items-start justify-between gap-3 mb-2 shrink-0">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 mb-0.5 text-[var(--cyan)]">
                <Cpu className="h-3.5 w-3.5" />
              </div>
              <h1 className="font-serif text-xl md:text-2xl text-[var(--text-h)] leading-tight truncate">
                AI Synthesis in Progress
              </h1>
              <p className="mt-0.5 text-[11px] text-[var(--muted)] truncate">
                Project &apos;{projectName}&apos; · neural core active
              </p>
            </div>
            <div className="shrink-0 flex items-center gap-1.5 rounded-full border border-[var(--green)]/30 bg-[var(--green)]/10 px-2 py-1 text-[9px] tracking-[0.12em] uppercase text-[var(--green)]">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--green)] pulse-dot" />
              Core Active
            </div>
          </div>

          <div className="relative rounded-xl overflow-hidden border border-[var(--border-strong)] bg-black/60 h-[38%] min-h-[140px] max-h-[220px] shrink-0">
            <video
              className="absolute inset-0 h-full w-full object-cover opacity-30"
              src={originalVideoUrl(jobId)}
              muted
              playsInline
              preload="metadata"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/45 to-black/25" />
            <div className="absolute top-2 left-2 flex gap-1.5">
              <span className="rounded bg-black/50 border border-white/10 px-1.5 py-0.5 text-[9px] text-[var(--muted)]">
                1080p ProRes
              </span>
              <span className="rounded bg-[var(--violet)]/30 border border-[var(--violet)]/40 px-1.5 py-0.5 text-[9px] text-[#e9d5ff]">
                AI Enhanced
              </span>
            </div>
            <div className="absolute inset-0 flex flex-col items-center justify-center px-3 text-center">
              <div className="mb-1.5 flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--violet)]/25 border border-[var(--violet)]/40">
                <Film className="h-4 w-4 text-[#e9d5ff]" />
              </div>
              <p className="text-sm text-[var(--text-h)]">Processing your video</p>
              <p className="text-[11px] text-[var(--muted)]">
                {pct}% · {status.replace(/_/g, ' ')}
              </p>
              <ul className="mt-2 flex flex-wrap justify-center gap-x-3 gap-y-1 text-[10px]">
                {checklist.map((item) => (
                  <li key={item.label} className="flex items-center gap-1">
                    {item.done ? (
                      <Check className="h-3 w-3 text-[var(--cyan)]" />
                    ) : item.active ? (
                      <span className="h-2 w-2 rounded-full bg-[var(--violet)] pulse-dot" />
                    ) : (
                      <span className="h-2 w-2 rounded-full border border-white/20" />
                    )}
                    <span className={item.done || item.active ? 'text-[var(--text-h)]' : 'text-[var(--muted)]'}>
                      {item.label}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="absolute bottom-1.5 right-2.5 font-mono text-[10px] text-[var(--muted)]">
              {formatTimecode(job?.duration_seconds)}
            </div>
          </div>

          <div className="mt-3 space-y-2.5 overflow-y-auto min-h-0 flex-1 pr-1">
            {PIPELINE.map((step, i) => {
              const done = bucket > i || status === 'complete'
              const active = bucket === i && !failed && status !== 'complete'
              return (
                <div key={step.key} className="flex gap-2.5">
                  <div
                    className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${
                      active
                        ? 'border-[var(--violet)] bg-[var(--violet)]/20 text-[#e9d5ff]'
                        : done
                          ? 'border-[var(--cyan)]/40 bg-[var(--cyan)]/10 text-[var(--cyan)]'
                          : 'border-white/10 text-[var(--muted)]'
                    }`}
                  >
                    {done && !active ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : active ? (
                      <Waves className="h-3.5 w-3.5" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className={`text-xs ${active || done ? 'text-[var(--text-h)]' : 'text-[var(--muted)]'}`}>
                        {step.label}
                      </h3>
                      {active && (
                        <span className="text-[10px] font-mono text-[var(--cyan)]">{Math.max(pct, 1)}%</span>
                      )}
                    </div>
                    {active && (
                      <div className="mt-1 h-1 rounded-full bg-white/10 overflow-hidden">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-r from-[var(--cyan)] to-[var(--violet)]"
                          animate={{ width: `${Math.max(pct, 8)}%` }}
                        />
                      </div>
                    )}
                    <p className="mt-0.5 text-[10px] text-[var(--muted)]">{step.detail}</p>
                  </div>
                </div>
              )
            })}
            {failed && (
              <div className="rounded-lg border border-[var(--danger)]/30 bg-[var(--danger)]/10 p-2.5 text-xs text-[var(--danger)]">
                {job?.error_message || 'Processing failed'}{' '}
                <Link to="/" className="underline text-[var(--text-h)]">
                  Try again
                </Link>
              </div>
            )}
          </div>
        </section>

        <aside className="glass rounded-2xl p-3.5 md:p-4 flex flex-col min-h-0 overflow-hidden">
          <div className="flex items-center gap-1.5 mb-2.5 shrink-0">
            <Eye className="h-3.5 w-3.5 text-[var(--cyan)]" />
            <h2 className="text-[10px] tracking-[0.18em] uppercase text-[var(--text-h)]">
              Neural Vision Pipeline
            </h2>
          </div>

          <div className="grid grid-cols-2 gap-2 mb-2.5 shrink-0">
            {visionCards.map((scene, i) => {
              const thumb = thumbnailUrl(scene.thumbnail_path)
              const titles = ['Subject Identified', 'Environment Scan']
              const tags =
                i === 0
                  ? [
                      { label: 'Face', cls: 'bg-[var(--violet)]/25 text-[#e9d5ff]' },
                      { label: 'Low Light', cls: 'bg-[var(--cyan)]/15 text-[var(--cyan)]' },
                    ]
                  : [
                      { label: 'Exterior', cls: 'bg-[var(--green)]/15 text-[var(--green)]' },
                      { label: 'Urban', cls: 'bg-[var(--violet)]/25 text-[#e9d5ff]' },
                    ]
              return (
                <div
                  key={`${scene.scene_index}-${i}`}
                  className="rounded-lg overflow-hidden border border-[var(--border)] bg-black/40"
                >
                  <div className="aspect-[16/10] relative bg-[var(--surface-solid)]">
                    {thumb ? (
                      <img src={thumb} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <div className="h-full w-full flex items-center justify-center text-[var(--muted)] text-[9px]">
                        Scene {i + 1}
                      </div>
                    )}
                    <span className="absolute top-1 right-1 font-mono text-[9px] text-white/80 bg-black/50 px-1 rounded">
                      {formatShort(scene.start)}
                    </span>
                  </div>
                  <div className="p-1.5">
                    <p className="text-[10px] text-[var(--text-h)] mb-1">{titles[i]}</p>
                    <div className="flex flex-wrap gap-1">
                      {tags.map((t) => (
                        <span key={t.label} className={`text-[8px] px-1 py-0.5 rounded ${t.cls}`}>
                          {t.label}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="flex-1 min-h-0 rounded-xl border border-[var(--border)] bg-black/35 p-3 mb-2.5 overflow-hidden flex flex-col">
            <div className="flex items-center gap-1.5 mb-1.5 shrink-0">
              <span className="h-1.5 w-1.5 rounded-full bg-[var(--violet)] pulse-dot" />
              <span className="text-[9px] tracking-[0.14em] uppercase text-[var(--muted)]">
                Live Transcript Stream
              </span>
            </div>
            <div className="h-6 mb-1.5 overflow-hidden opacity-70 shrink-0">
              <svg viewBox="0 0 400 40" className="w-[200%] h-full wave-scroll text-[var(--violet)]">
                <path
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  d="M0 20 Q 25 5 50 20 T 100 20 T 150 20 T 200 20 T 250 20 T 300 20 T 350 20 T 400 20 T 450 20 T 500 20 T 550 20 T 600 20 T 650 20 T 700 20 T 750 20 T 800 20"
                />
              </svg>
            </div>
            <p className="font-serif italic text-xs leading-snug text-[var(--text)] overflow-y-auto min-h-0">
              {liveQuote}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2 shrink-0">
            <Link
              to="/"
              className="flex items-center justify-center gap-1.5 rounded-full border border-white/10 bg-white/5 py-2 text-xs text-[var(--text-h)] hover:border-[var(--danger)]/50 hover:text-[var(--danger)] transition-colors"
            >
              <StopCircle className="h-3.5 w-3.5 text-[var(--danger)]" />
              Abort
            </Link>
            <button
              type="button"
              className="flex items-center justify-center gap-1.5 rounded-full border border-white/10 bg-white/5 py-2 text-xs text-[var(--text-h)] hover:border-[var(--cyan)]/40 transition-colors"
            >
              <Settings2 className="h-3.5 w-3.5 text-[var(--muted)]" />
              Settings
            </button>
          </div>
        </aside>
      </div>
    </div>
  )
}
