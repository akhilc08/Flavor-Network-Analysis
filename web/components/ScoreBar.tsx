'use client'
import { useEffect, useState } from 'react'

interface ScoreBarProps {
  label: string
  value: number          // 0-1
  variant: 'pairing' | 'surprise'
}

const GRADIENTS = {
  pairing: 'linear-gradient(90deg, #c4622a, #e8845a)',
  surprise: 'linear-gradient(90deg, #4a7c4e, #6aab6e)',
}

export default function ScoreBar({ label, value, variant }: ScoreBarProps) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    // Defer to next frame so CSS transition fires
    const id = requestAnimationFrame(() => setWidth(value * 100))
    return () => cancelAnimationFrame(id)
  }, [value])

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex justify-between items-baseline">
        <span className="font-sans text-[10px] font-semibold tracking-[0.1em] uppercase text-warm-mid">
          {label}
        </span>
        <span className="font-serif text-sm text-dark">{value.toFixed(3)}</span>
      </div>
      <div className="h-[3px] bg-muted rounded-full overflow-hidden">
        <div
          className="h-full rounded-full score-bar-fill"
          style={{ width: `${width}%`, background: GRADIENTS[variant] }}
        />
      </div>
    </div>
  )
}
