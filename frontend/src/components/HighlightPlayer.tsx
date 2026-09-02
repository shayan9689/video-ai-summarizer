import { useState } from 'react'
import { highlightReelUrl, originalVideoUrl } from '../api/client'

type Props = {
  jobId: string
  videoRef: React.RefObject<HTMLVideoElement | null>
}

export default function HighlightPlayer({ jobId, videoRef }: Props) {
  const [mode, setMode] = useState<'highlights' | 'full'>('highlights')
  const src = mode === 'highlights' ? highlightReelUrl(jobId) : originalVideoUrl(jobId)

  return (
    <div>
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <h3 className="font-serif text-xl text-[var(--text-h)]">Playback</h3>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setMode('highlights')}
            className={`rounded-full px-3 py-1.5 border transition-colors ${
              mode === 'highlights'
                ? 'border-[var(--cyan)] text-[var(--cyan)] bg-[var(--cyan)]/10'
                : 'border-white/10 text-[var(--muted)]'
            }`}
          >
            Watch highlights
          </button>
          <button
            type="button"
            onClick={() => setMode('full')}
            className={`rounded-full px-3 py-1.5 border transition-colors ${
              mode === 'full'
                ? 'border-[var(--violet)] text-[#e9d5ff] bg-[var(--violet)]/15'
                : 'border-white/10 text-[var(--muted)]'
            }`}
          >
            Watch full video
          </button>
        </div>
      </div>
      <video
        key={src}
        ref={videoRef}
        src={src}
        controls
        className="w-full max-h-[420px] rounded-2xl bg-black border border-[var(--border)]"
      />
    </div>
  )
}
