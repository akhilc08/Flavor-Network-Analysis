'use client'
import { useState, useRef } from 'react'

interface StarRatingProps {
  value: number
  onChange: (v: number) => void
}

export default function StarRating({ value, onChange }: StarRatingProps) {
  const [hovered, setHovered] = useState(0)
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([])

  function handleKeyDown(star: number, e: React.KeyboardEvent<HTMLButtonElement>) {
    const key = e.key
    let nextStar: number | null = null

    if (key === 'ArrowRight' || key === 'ArrowUp') {
      if (star < 5) {
        nextStar = star + 1
        e.preventDefault()
      }
    } else if (key === 'ArrowLeft' || key === 'ArrowDown') {
      if (star > 1) {
        nextStar = star - 1
        e.preventDefault()
      }
    }

    if (nextStar !== null) {
      const nextButton = buttonRefs.current[nextStar - 1]
      if (nextButton) {
        onChange(nextStar)
        nextButton.focus()
      }
    }
  }

  return (
    <div
      role="radiogroup"
      aria-label="Star rating"
      className="flex gap-1"
      onMouseLeave={() => setHovered(0)}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = hovered > 0 ? star <= hovered : star <= value
        const color = hovered > 0 && star <= hovered
          ? '#e8845a'
          : star <= value
            ? '#c4622a'
            : '#e8d5bc'

        return (
          <button
            key={star}
            ref={(el) => {
              buttonRefs.current[star - 1] = el
            }}
            type="button"
            role="radio"
            aria-label={`${star} stars`}
            aria-checked={value === star}
            onClick={() => onChange(star)}
            onMouseEnter={() => setHovered(star)}
            onKeyDown={(e) => handleKeyDown(star, e)}
            style={{ color, fontSize: '28px', fontFamily: 'Georgia, serif', lineHeight: 1 }}
            className="bg-transparent border-none cursor-pointer p-0 leading-none transition-colors duration-100"
          >
            {filled ? '★' : '☆'}
          </button>
        )
      })}
    </div>
  )
}
