import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Cpu, Link2, Upload } from 'lucide-react'
import { submitVideoUrl, uploadVideo } from '../api/client'

const ALLOWED = ['.mp4', '.mov', '.mkv']
const MAX_MB = 80

type Mode = 'upload' | 'link'

export default function VideoUpload() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [mode, setMode] = useState<Mode>('upload')
  const [dragging, setDragging] = useState(false)
  const [url, setUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)

  function validateFile(file: File): string | null {
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED.includes(ext)) return `Unsupported type. Use ${ALLOWED.join(', ')}`
    if (file.size > MAX_MB * 1024 * 1024) return `File exceeds ${MAX_MB}MB limit`
    return null
  }

  async function handleFile(file: File) {
    const err = validateFile(file)
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setBusy(true)
    setProgress(0)
    try {
      const res = await uploadVideo(file, setProgress)
      navigate(`/jobs/${res.job_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setBusy(false)
    }
  }

  async function handleUrl() {
    const trimmed = url.trim()
    if (!trimmed) {
      setError('Paste a YouTube, Vimeo, or direct video link')
      return
    }
    setError(null)
    setBusy(true)
    try {
      const res = await submitVideoUrl(trimmed)
      navigate(`/jobs/${res.job_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Link failed')
      setBusy(false)
    }
  }

  return (
    <div className="px-4 md:px-8 py-2 max-w-[820px] mx-auto w-full">
      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-2xl p-5 md:p-6"
      >
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2 mb-1 text-[var(--cyan)]">
              <Cpu className="h-3.5 w-3.5" />
            </div>
            <h1 className="font-serif text-2xl md:text-3xl text-[var(--text-h)] leading-tight">
              Initialize Neural Synthesis
            </h1>
            <p className="mt-1.5 text-xs text-[var(--muted)] max-w-md">
              Upload a file or paste a link. Clips under 2 minutes usually finish in ~2–3 minutes.
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-1.5 rounded-full border border-[var(--green)]/30 bg-[var(--green)]/10 px-2.5 py-1 text-[9px] tracking-[0.14em] uppercase text-[var(--green)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--green)] pulse-dot" />
            Core Ready
          </div>
        </div>

        <div className="mb-4 inline-flex rounded-full border border-white/10 bg-black/30 p-1 text-xs">
          <button
            type="button"
            onClick={() => setMode('upload')}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors ${
              mode === 'upload'
                ? 'bg-[var(--violet)]/25 text-[#e9d5ff]'
                : 'text-[var(--muted)] hover:text-[var(--text-h)]'
            }`}
          >
            <Upload className="h-3.5 w-3.5" />
            Upload file
          </button>
          <button
            type="button"
            onClick={() => setMode('link')}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors ${
              mode === 'link'
                ? 'bg-[var(--cyan)]/15 text-[var(--cyan)]'
                : 'text-[var(--muted)] hover:text-[var(--text-h)]'
            }`}
          >
            <Link2 className="h-3.5 w-3.5" />
            Paste link
          </button>
        </div>

        {mode === 'upload' ? (
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragging(false)
              const file = e.dataTransfer.files?.[0]
              if (file) void handleFile(file)
            }}
            className={`relative rounded-xl border border-dashed px-5 py-10 text-center transition-all ${
              dragging
                ? 'border-[var(--cyan)] bg-[var(--cyan)]/5'
                : 'border-[var(--border-strong)] bg-black/30'
            }`}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".mp4,.mov,.mkv,video/mp4,video/quicktime,video/x-matroska"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) void handleFile(file)
              }}
            />
            <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--violet)]/20 border border-[var(--violet)]/40 text-[#e9d5ff]">
              <Upload className="h-5 w-5" />
            </div>
            <p className="text-[var(--text-h)] text-sm mb-0.5">Drop video into the neural core</p>
            <p className="text-xs text-[var(--muted)] mb-4">
              MP4 / MOV / MKV · under 2 min · max {MAX_MB}MB
            </p>
            <button
              type="button"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
              className="rounded-full bg-gradient-to-r from-[var(--violet)] to-[var(--cyan)] px-6 py-2 text-sm font-medium text-black disabled:opacity-50"
            >
              {busy ? 'Uploading…' : 'Choose file'}
            </button>
            {busy && mode === 'upload' && (
              <div className="mt-5 mx-auto max-w-xs">
                <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--cyan)] to-[var(--violet)]"
                    animate={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-[10px] font-mono text-[var(--muted)] mt-1.5">{progress}%</p>
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-xl border border-[var(--border-strong)] bg-black/30 p-5">
            <label className="block text-xs text-[var(--muted)] mb-2 tracking-wide uppercase">
              Video URL
            </label>
            <div className="flex flex-col sm:flex-row gap-2">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://youtube.com/watch?v=… or direct .mp4 link"
                className="flex-1 rounded-full border border-white/10 bg-black/40 px-4 py-2.5 text-sm text-[var(--text-h)] placeholder:text-[var(--muted)] outline-none focus:border-[var(--cyan)]/50"
                disabled={busy}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void handleUrl()
                }}
              />
              <button
                type="button"
                disabled={busy}
                onClick={() => void handleUrl()}
                className="rounded-full bg-gradient-to-r from-[var(--cyan)] to-[var(--violet)] px-6 py-2.5 text-sm font-medium text-black disabled:opacity-50 shrink-0"
              >
                {busy ? 'Fetching…' : 'Analyze link'}
              </button>
            </div>
            <p className="mt-2 text-[11px] text-[var(--muted)]">
              Best with Vimeo or a direct .mp4 link. YouTube often blocks cloud servers — if it
              fails, download the clip and use <span className="text-[var(--text-h)]">Upload file</span>.
              Keep clips ≤ 2 minutes.
            </p>
          </div>
        )}

        {error && (
          <p
            className="mt-3 text-center text-sm text-[var(--danger)] max-w-xl mx-auto leading-relaxed"
            role="alert"
          >
            {error}
          </p>
        )}
      </motion.section>
    </div>
  )
}
