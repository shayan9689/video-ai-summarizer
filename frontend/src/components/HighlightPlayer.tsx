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
        <h3 className="text-lg">Playback</h3>
        <div className="flex gap-2 text-xs">
          <button
            type="button"
            onClick={() => setMode('highlights')}
            className={`px-3 py-1.5 border transition-colors ${
              mode === 'highlights'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-[var(--border)] text-[var(--muted)]'
            }`}
          >
            Watch highlights
          </button>
          <button
            type="button"
            onClick={() => setMode('full')}
            className={`px-3 py-1.5 border transition-colors ${
              mode === 'full'
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-[var(--border)] text-[var(--muted)]'
            }`}
          >
            Watch full video
          </button>
          <a
            href={highlightReelUrl(jobId)}
            download
            className="px-3 py-1.5 bg-[var(--accent)] text-[var(--bg)] font-medium"
          >
            Download reel
          </a>
        </div>
      </div>
      <video
        key={src}
        ref={videoRef}
        src={src}
        controls
        className="w-full max-h-[420px] bg-black"
      />
    </div>
  )
}
