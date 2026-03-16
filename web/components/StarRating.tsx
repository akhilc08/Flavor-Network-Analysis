'use client'
import { useState } from 'react'

interface StarRatingProps {
  value: number
  onChange: (v: number) => void
}

export default function StarRating({ value, onChange }: StarRatingProps) {
  const [hovered, setHovered] = useState(0)

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
            type="button"
            role="radio"
            aria-label={`${star} stars`}
            aria-checked={value === star}
            onClick={() => onChange(star)}
            onMouseEnter={() => setHovered(star)}
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
