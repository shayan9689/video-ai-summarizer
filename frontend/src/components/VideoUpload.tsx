import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Cpu, Upload } from 'lucide-react'
import { uploadVideo } from '../api/client'

const ALLOWED = ['.mp4', '.mov', '.mkv']
const MAX_MB = 80

export default function VideoUpload() {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  function validate(file: File): string | null {
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    if (!ALLOWED.includes(ext)) return `Unsupported type. Use ${ALLOWED.join(', ')}`
    if (file.size > MAX_MB * 1024 * 1024) return `File exceeds ${MAX_MB}MB limit`
    return null
  }

  async function handleFile(file: File) {
    const err = validate(file)
    if (err) {
      setError(err)
      return
    }
    setError(null)
    setUploading(true)
    setProgress(0)
    try {
      const res = await uploadVideo(file, setProgress)
      navigate(`/jobs/${res.job_id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <div className="px-4 md:px-8 pb-10 max-w-[900px] mx-auto w-full">
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass rounded-[1.75rem] p-6 md:p-10"
      >
        <div className="flex items-start justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2 mb-2 text-[var(--cyan)]">
              <Cpu className="h-4 w-4" />
            </div>
            <h1 className="font-serif text-3xl md:text-5xl text-[var(--text-h)] leading-tight">
              Initialize Neural Synthesis
            </h1>
            <p className="mt-3 text-sm text-[var(--muted)] max-w-lg">
              Drop a short video into the core. Whisper, scene analysis, and highlight rendering
              run as a single pipeline — typically 2–3 minutes for clips under 2 minutes.
            </p>
          </div>
          <div className="hidden sm:flex items-center gap-2 rounded-full border border-[var(--green)]/30 bg-[var(--green)]/10 px-3 py-1.5 text-[10px] tracking-[0.14em] uppercase text-[var(--green)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[var(--green)] pulse-dot" />
            Core Ready
          </div>
        </div>

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
          className={`relative rounded-2xl border border-dashed px-6 py-16 text-center transition-all ${
            dragging
              ? 'border-[var(--cyan)] bg-[var(--cyan)]/5 glow-cyan'
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
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--violet)]/20 border border-[var(--violet)]/40 text-[#e9d5ff]">
            <Upload className="h-6 w-6" />
          </div>
          <p className="text-[var(--text-h)] text-lg mb-1">Drop video into the neural core</p>
          <p className="text-sm text-[var(--muted)] mb-6">
            MP4 / MOV / MKV · under 2 minutes · max {MAX_MB}MB
          </p>
          <button
            type="button"
            disabled={uploading}
            onClick={() => inputRef.current?.click()}
            className="rounded-full bg-gradient-to-r from-[var(--violet)] to-[var(--cyan)] px-7 py-2.5 text-sm font-medium text-black disabled:opacity-50"
          >
            {uploading ? 'Uploading…' : 'Choose file'}
          </button>

          {uploading && (
            <div className="mt-8 mx-auto max-w-xs">
              <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-[var(--cyan)] to-[var(--violet)]"
                  animate={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs font-mono text-[var(--muted)] mt-2">{progress}%</p>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-4 text-center text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        )}
      </motion.section>
    </div>
  )
}
