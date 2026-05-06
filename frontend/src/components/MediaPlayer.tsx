'use client'

import { forwardRef, useEffect, useMemo, useRef, useState } from 'react'
import { FileAudio, FileVideo, Volume2, VolumeX, Play, Pause } from 'lucide-react'
import { motion } from 'framer-motion'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface MediaPlayerProps {
  src: string
  type: string
  fileName: string
  onTimeUpdate?: (currentTime: number) => void
}

type MediaEl = HTMLMediaElement

export const MediaPlayer = forwardRef<MediaEl, MediaPlayerProps>(
  ({ src, type, fileName, onTimeUpdate }, ref) => {
    const localRef = useRef<MediaEl>(null)
    const mediaRef = (ref ?? localRef) as React.RefObject<MediaEl>

    const [isPlaying, setIsPlaying] = useState(false)
    const [isMuted, setIsMuted] = useState(false)
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [isLoading, setIsLoading] = useState(false)

    const [targetTimeRaw, setTargetTimeRaw] = useState('')

    useEffect(() => {
      const media = mediaRef && 'current' in mediaRef ? mediaRef.current : null
      if (!media) return

      const handleTimeUpdate = () => {
        const time = media.currentTime
        setCurrentTime(time)
        onTimeUpdate?.(time)
      }

      const handleLoadedMetadata = () => {
        setDuration(media.duration)
      }

      const handlePlay = () => {
        setIsPlaying(true)
      }

      const handlePause = () => {
        setIsPlaying(false)
      }

      const handleLoadStart = () => {
        setIsLoading(true)
      }

      const handleCanPlay = () => {
        setIsLoading(false)
      }

      media.addEventListener('timeupdate', handleTimeUpdate)
      media.addEventListener('loadedmetadata', handleLoadedMetadata)
      media.addEventListener('play', handlePlay)
      media.addEventListener('pause', handlePause)
      media.addEventListener('loadstart', handleLoadStart)
      media.addEventListener('canplay', handleCanPlay)

      return () => {
        media.removeEventListener('timeupdate', handleTimeUpdate)
        media.removeEventListener('loadedmetadata', handleLoadedMetadata)
        media.removeEventListener('play', handlePlay)
        media.removeEventListener('pause', handlePause)
        media.removeEventListener('loadstart', handleLoadStart)
        media.removeEventListener('canplay', handleCanPlay)
      }
    }, [mediaRef, onTimeUpdate])

    const formatTime = (seconds: number) => {
      if (!Number.isFinite(seconds) || seconds < 0) return '0:00'
      const mins = Math.floor(seconds / 60)
      const secs = Math.floor(seconds % 60)
      return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const parseTargetTime = useMemo(() => {
      // Supports: "123" (seconds) or "mm:ss" (e.g. 03:12)
      const raw = targetTimeRaw.trim()
      if (!raw) return null

      if (/^\d+(\.\d+)?$/.test(raw)) {
        const v = Number(raw)
        return Number.isFinite(v) ? v : null
      }

      const mmss = raw.match(/^(\d{1,}):(\d{1,2})$/)
      if (!mmss) return null

      const mins = Number(mmss[1])
      const secs = Number(mmss[2])
      if (!Number.isFinite(mins) || !Number.isFinite(secs)) return null

      if (secs < 0 || secs >= 60) {
        // tolerate but clamp
        const clampedSecs = Math.max(0, Math.min(59, secs))
        return mins * 60 + clampedSecs
      }

      return mins * 60 + secs
    }, [targetTimeRaw])

    const seekToParsedTime = () => {
      const media = mediaRef && 'current' in mediaRef ? mediaRef.current : null
      if (!media) return
      const t = parseTargetTime
      if (t === null) return

      const bounded = Math.max(0, Math.min(t, Number.isFinite(duration) && duration > 0 ? duration : t))
      media.currentTime = bounded
      setCurrentTime(bounded)
      void media.play()
    }

    const handlePlayPause = () => {
      const media = mediaRef && 'current' in mediaRef ? mediaRef.current : null
      if (!media) return
      if (isPlaying) media.pause()
      else void media.play()
    }

    const handleMute = () => {
      const media = mediaRef && 'current' in mediaRef ? mediaRef.current : null
      if (!media) return
      media.muted = !isMuted
      setIsMuted((prev) => !prev)
    }

    const handleProgressChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const media = mediaRef && 'current' in mediaRef ? mediaRef.current : null
      if (!media) return
      const newTime = parseFloat(e.target.value)
      media.currentTime = newTime
      setCurrentTime(newTime)
    }

    const isAudio = type.startsWith('audio/')
    const isVideo = type.startsWith('video/')

    return (
      <div className="w-full space-y-4">
        {isAudio && (
          <audio ref={mediaRef} preload="metadata">
            <source src={src} type={type} />
            Your browser does not support the audio element.
          </audio>
        )}

        {isVideo && (
          <video
            ref={(mediaRef as unknown) as React.RefObject<HTMLVideoElement>}
            preload="metadata"
            className="w-full rounded-xl bg-black"
          >
            <source src={src} type={type} />
            Your browser does not support the video element.
          </video>
        )}

        <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 space-y-4">
          <div className="flex items-center gap-3">
            {isAudio ? (
              <FileAudio className="w-5 h-5 text-pink-400 flex-shrink-0" />
            ) : (
              <FileVideo className="w-5 h-5 text-indigo-400 flex-shrink-0" />
            )}
            <span className="text-sm text-slate-300 truncate font-medium">{fileName}</span>
          </div>

          {/* Timestamp-based playback button */}
          <div className="flex items-center gap-2">
            <div className="flex-1">
              <label className="text-[11px] text-slate-400 block mb-1">Play from timestamp</label>
              <Input
                value={targetTimeRaw}
                onChange={(e) => setTargetTimeRaw(e.target.value)}
                placeholder="e.g. 12.5 or 03:12"
                className="bg-slate-900/30 border-slate-700 text-white h-10 rounded-xl"
              />
            </div>
            <div className="pt-5">
              <Button
                type="button"
                onClick={seekToParsedTime}
                disabled={parseTargetTime === null}
                className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl h-10 px-4"
              >
                Play
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <input
              type="range"
              min="0"
              max={duration || 0}
              value={currentTime}
              onChange={handleProgressChange}
              className="w-full h-1 bg-slate-700 rounded-full appearance-none cursor-pointer accent-indigo-500"
              style={{
                background: `linear-gradient(to right, rgb(99, 102, 241) 0%, rgb(99, 102, 241) ${
                  duration ? (currentTime / duration) * 100 : 0
                }%, rgb(51, 65, 85) ${duration ? (currentTime / duration) * 100 : 0}%, rgb(51, 65, 85) 100%)`,
              }}
            />
            <div className="flex justify-between text-xs text-slate-400">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <motion.button
              onClick={handlePlayPause}
              disabled={isLoading}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center justify-center w-10 h-10 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-600 text-white transition-colors"
            >
              {isLoading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                >
                  <span className="block w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
                </motion.div>
              ) : isPlaying ? (
                <Pause className="w-5 h-5" />
              ) : (
                <Play className="w-5 h-5 ml-0.5" />
              )}
            </motion.button>

            <motion.button
              onClick={handleMute}
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
            >
              {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
            </motion.button>
          </div>
        </div>
      </div>
    )
  }
)

MediaPlayer.displayName = 'MediaPlayer'

