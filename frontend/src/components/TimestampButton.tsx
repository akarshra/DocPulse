'use client'

import { Clock } from 'lucide-react'
import { motion } from 'framer-motion'

interface TimestampButtonProps {
  startTime: number
  endTime: number
  onPlay: (startTime: number) => void
  isPlaying?: boolean
  variant?: 'compact' | 'full'
}

export function TimestampButton({
  startTime,
  endTime,
  onPlay,
  isPlaying = false,
  variant = 'compact'
}: TimestampButtonProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const startFormatted = formatTime(startTime)
  const endFormatted = formatTime(endTime)

  if (variant === 'full') {
    return (
      <motion.button
        onClick={() => onPlay(startTime)}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
        className={`w-full flex items-center justify-between px-4 py-2 rounded-lg font-medium transition-all ${
          isPlaying
            ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/50'
            : 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/20'
        }`}
      >
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 flex-shrink-0" />
          <span>{startFormatted} - {endFormatted}</span>
        </div>
        <span className="text-xs opacity-70">
          {Math.floor(endTime - startTime)}s
        </span>
      </motion.button>
    )
  }

  // Compact variant
  return (
    <motion.button
      onClick={() => onPlay(startTime)}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      title={`Play from ${startFormatted} to ${endFormatted}`}
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded transition-all ${
        isPlaying
          ? 'bg-indigo-500 text-white shadow-md'
          : 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-500/20'
      }`}
    >
      <Clock className="w-3 h-3 flex-shrink-0" />
      <span className="hidden sm:inline">{startFormatted}</span>
      <span className="sm:hidden">{startFormatted.split(':')[0]}m</span>
    </motion.button>
  )
}
