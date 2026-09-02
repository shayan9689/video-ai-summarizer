import { thumbnailUrl, type HighlightSegment, type Scene } from '../api/client'

type Props = {
  scenes: Scene[]
  scored?: HighlightSegment[]
  onSeek: (seconds: number) => void
}

export default function SceneTimeline({ scenes, scored, onSeek }: Props) {
  const scoreMap = new Map((scored || []).map((s) => [s.scene_index, s]))
  const selected = new Set(
    (scored || []).filter((s) => s.selected !== false && s.selected !== undefined
      ? s.selected
      : false).map((s) => s.scene_index),
  )
  // If segments list is the selected set only, mark those indices
  if (selected.size === 0 && scored?.length) {
    for (const s of scored) {
      if (s.selected !== false) selected.add(s.scene_index)
    }
  }

  return (
    <div>
      <h3 className="text-lg mb-3">Scene timeline</h3>
      <div className="flex gap-3 overflow-x-auto pb-3 snap-x">
        {scenes.map((scene) => {
          const score = scoreMap.get(scene.scene_index)?.score ?? scene.motion_score
          const selectedFlag = selected.has(scene.scene_index)
          const thumb = thumbnailUrl(scene.thumbnail_path)
          return (
            <button
              key={scene.scene_index}
              type="button"
              onClick={() => onSeek(scene.start)}
              className={`snap-start shrink-0 w-36 text-left ${
                selectedFlag ? 'opacity-100' : 'opacity-70'
              }`}
            >
              <div
                className={`aspect-video bg-[var(--surface)] overflow-hidden border ${
                  selectedFlag ? 'border-[var(--accent)]' : 'border-[var(--border)]'
                }`}
              >
                {thumb ? (
                  <img src={thumb} alt="" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-[var(--muted)] text-xs">
                    Scene {scene.scene_index + 1}
                  </div>
                )}
              </div>
              <div className="mt-1.5 h-1 bg-[var(--border)]">
                <div
                  className="h-full bg-[var(--accent)]"
                  style={{ width: `${Math.max(8, Math.min(100, score * 100))}%` }}
                />
              </div>
              <p className="text-[10px] text-[var(--muted)] mt-1">
                {formatTs(scene.start)}
                {selectedFlag ? ' · in reel' : ''}
              </p>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function formatTs(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}
