import type { Summary } from '../api/client'

type Props = {
  summary: Summary
  onSeek: (seconds: number) => void
}

export default function SummaryPanel({ summary, onSeek }: Props) {
  async function copyMarkdown() {
    const md = [
      '## Overview',
      summary.overview,
      '',
      '## Key points',
      ...summary.key_points.map((p) => `- ${p}`),
    ].join('\n')
    await navigator.clipboard.writeText(md)
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between gap-4 mb-3">
          <h3 className="text-lg">Overview</h3>
          <button
            type="button"
            onClick={() => void copyMarkdown()}
            className="text-xs text-[var(--accent)] hover:underline"
          >
            Copy shareable summary
          </button>
        </div>
        <p className="text-[var(--text)] leading-relaxed">{summary.overview}</p>
      </div>

      <div>
        <h3 className="text-lg mb-3">Key points</h3>
        <ul className="space-y-2">
          {summary.key_points.map((point) => (
            <li key={point} className="pl-3 border-l border-[var(--accent)] text-sm leading-relaxed">
              {point}
            </li>
          ))}
        </ul>
      </div>

      {summary.notable_quotes.length > 0 && (
        <div>
          <h3 className="text-lg mb-3">Notable quotes</h3>
          <div className="flex flex-wrap gap-2">
            {summary.notable_quotes.map((q) => (
              <button
                key={`${q.timestamp}-${q.text.slice(0, 24)}`}
                type="button"
                onClick={() => onSeek(q.timestamp)}
                className="text-left text-sm px-3 py-2 bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)] transition-colors max-w-full"
              >
                <span className="text-[var(--accent)] text-xs mr-2">
                  {formatTs(q.timestamp)}
                </span>
                “{q.text}”
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function formatTs(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${String(sec).padStart(2, '0')}`
}
