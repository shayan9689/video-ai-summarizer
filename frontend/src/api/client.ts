const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export type JobStatusResponse = {
  job_id: string
  status: string
  progress_percent: number
  error_message?: string | null
  duration_seconds?: number | null
  filename?: string
}

export type Summary = {
  overview: string
  key_points: string[]
  notable_quotes: { text: string; timestamp: number }[]
}

export type Scene = {
  scene_index: number
  start: number
  end: number
  motion_score: number
  thumbnail_path?: string | null
}

export type HighlightSegment = {
  scene_index: number
  start: number
  end: number
  score: number
  selected?: boolean
}

export type FullResult = {
  status: string
  progress_percent: number
  error_message?: string | null
  video_metadata: {
    filename: string
    duration_seconds: number | null
    width: number | null
    height: number | null
    fps: number | null
    codec: string | null
  }
  summary: Summary | null
  highlights: {
    segments: HighlightSegment[]
    all_scored?: HighlightSegment[]
    total_duration: number
  } | null
  scenes: { scenes: Scene[] } | null
}

export function uploadVideo(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<{ job_id: string; duration_seconds: number; status: string }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/api/videos/upload`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }
    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText)
        if (xhr.status >= 200 && xhr.status < 300) resolve(data)
        else reject(new Error(data.detail || 'Upload failed'))
      } catch {
        reject(new Error('Upload failed'))
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    const form = new FormData()
    form.append('file', file)
    xhr.send(form)
  })
}

export async function submitVideoUrl(
  url: string,
): Promise<{ job_id: string; duration_seconds: number; status: string }> {
  const res = await fetch(`${API_BASE}/api/videos/from-url`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = data.detail
    throw new Error(typeof detail === 'string' ? detail : 'Could not process this link')
  }
  return data
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE}/api/videos/${jobId}/status`)
  if (!res.ok) throw new Error('Failed to fetch status')
  return res.json()
}

export async function getFullResult(jobId: string): Promise<FullResult> {
  const res = await fetch(`${API_BASE}/api/videos/${jobId}/full-result`)
  if (!res.ok) throw new Error('Failed to fetch results')
  return res.json()
}

export function highlightReelUrl(jobId: string): string {
  return `${API_BASE}/api/videos/${jobId}/download/highlight-reel`
}

export function originalVideoUrl(jobId: string): string {
  return `${API_BASE}/api/videos/${jobId}/download/original`
}

export function thumbnailUrl(relPath: string | null | undefined): string | undefined {
  if (!relPath) return undefined
  return `${API_BASE}/static/uploads/${relPath}`
}

export function connectJobSocket(
  jobId: string,
  onMessage: (data: JobStatusResponse & { type?: string }) => void,
): WebSocket {
  const base = API_BASE || window.location.origin
  const wsBase = base.replace(/^http/, 'ws')
  const ws = new WebSocket(`${wsBase}/ws/videos/${jobId}`)
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data)
      if (data.type === 'ping') return
      onMessage(data)
    } catch {
      /* ignore */
    }
  }
  return ws
}
