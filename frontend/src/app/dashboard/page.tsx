'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { motion, AnimatePresence } from 'framer-motion'
import { FileText, LogOut, UploadCloud, RefreshCw, Cpu, FileAudio, FileVideo, ChevronRight, MessageSquare, AlertCircle } from 'lucide-react'
import { TimestampButton } from '@/components/TimestampButton'
import { MediaPlayer } from '@/components/MediaPlayer'
import { useStreamingChat } from '@/hooks/useStreamingChat'
import { v4 as uuidv4 } from 'uuid'

interface UploadedFile {
  id: string
  name: string
  type: string
  status: string
  url: string
}

interface TimestampRange {
  start_time: number
  end_time: number
  chunk_index?: number
}

interface Message {
  id: string
  question: string
  answer: string
  timestamp_ranges: TimestampRange[]
  source_file?: string
  isStreaming: boolean
  error?: string
}

export default function Dashboard() {
  const router = useRouter()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null)
  const [summary, setSummary] = useState<string>('')
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(false)

  const playerRef = useRef<HTMLMediaElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Streaming chat hook
  const { stream } = useStreamingChat({
    onMessageStart: () => {},
    onTokenReceived: (token) => {
      setMessages((prev) => {
        const newMsgs = [...prev]
        if (newMsgs.length > 0) {
          newMsgs[newMsgs.length - 1] = {
            ...newMsgs[newMsgs.length - 1],
            answer: newMsgs[newMsgs.length - 1].answer + token,
          }
        }
        return newMsgs
      })
    },
    onMetadataReceived: (metadata) => {
      setMessages((prev) => {
        const newMsgs = [...prev]
        if (newMsgs.length > 0) {
          newMsgs[newMsgs.length - 1] = {
            ...newMsgs[newMsgs.length - 1],
            timestamp_ranges: metadata.timestamp_ranges || [],
            source_file: metadata.source_file,
          }
        }
        return newMsgs
      })
    },
    onMessageComplete: (message) => {
      setMessages((prev) => {
        const newMsgs = [...prev]
        if (newMsgs.length > 0) {
          newMsgs[newMsgs.length - 1] = {
            ...message,
            isStreaming: false,
          }
        }
        return newMsgs
      })
    },
    onError: (error) => {
      setMessages((prev) => {
        const newMsgs = [...prev]
        if (newMsgs.length > 0) {
          newMsgs[newMsgs.length - 1] = {
            ...newMsgs[newMsgs.length - 1],
            isStreaming: false,
            error: error,
          }
        }
        return newMsgs
      })
    },
  })

  // Load session id on mount (avoid react-hooks/set-state-in-effect lint)
  // Load session id on mount (avoid lint false-positive)
  useEffect(() => {
    const sid = localStorage.getItem('sessionId')
    if (!sid) {
      router.push('/')
      return
    }

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessionId(sid)
  }, [router])





  const axiosConfig = {
    headers: { 'X-Session-ID': sessionId }
  }

  const fetchFiles = useCallback(async () => {
    try {
      const res = await axios.get('http://localhost:8000/api/files', {
        headers: { 'X-Session-ID': sessionId },
      })
      setFiles(res.data)
    } catch (error) {
      console.error('Error fetching files:', error)
    }
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return
    void (async () => {
      await fetchFiles()
    })()
  }, [sessionId, fetchFiles])



  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])




  const uploadFile = async (file: File) => {

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    try {
      await axios.post('http://localhost:8000/api/upload', formData, {
        headers: {
          'X-Session-ID': sessionId,
          'Content-Type': 'multipart/form-data'
        }
      })
      await fetchFiles()
    } catch (error) {
      console.error('Error uploading file:', error)
    }
    setUploading(false)
  }

  const processFile = async (fileId: string) => {
    try {
      await axios.post(`http://localhost:8000/api/process/${fileId}`, {}, axiosConfig)
      await fetchFiles()
    } catch (error) {
      console.error('Error processing file:', error)
    }
  }

  const getSummary = async (fileId: string) => {
    setLoading(true)
    try {
      const res = await axios.get(`http://localhost:8000/api/summary/${fileId}`, axiosConfig)
      setSummary(res.data.summary)
    } catch (error) {
      console.error('Error getting summary:', error)
    }
    setLoading(false)
  }

  const askQuestion = async () => {
    if (!selectedFile || !question.trim() || !sessionId) return

    const q = question
    const messageId = uuidv4()

    setQuestion('')

    // Add placeholder message
    setMessages(prev => [
      ...prev,
      {
        id: messageId,
        question: q,
        answer: '',
        timestamp_ranges: [],
        isStreaming: true
      }
    ])

    // Stream the response
    await stream(selectedFile.id, q, sessionId, messageId)
  }

  const jumpToTime = useCallback((time: number) => {
    if (playerRef.current) {
      playerRef.current.currentTime = time
      playerRef.current.play()
    }
  }, [])

  const handleLogout = () => {
    localStorage.removeItem('sessionId')
    router.push('/')
  }

  const getFileIcon = (type: string) => {
    if (type.startsWith('audio/')) return <FileAudio className="w-5 h-5 text-pink-400" />
    if (type.startsWith('video/')) return <FileVideo className="w-5 h-5 text-indigo-400" />
    return <FileText className="w-5 h-5 text-purple-400" />
  }

  if (!sessionId) return null

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Cpu className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-xl font-bold text-white tracking-wide">DocPulse AI</h1>
            </div>
            <div className="flex items-center gap-4">
              <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-slate-400 hidden sm:flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                Session Active
              </div>
              <Button onClick={handleLogout} variant="ghost" size="sm" className="text-slate-400 hover:text-white hover:bg-white/5">
                <LogOut className="w-4 h-4 mr-2" />
                Exit
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Left Panel: File List */}
          <div className="lg:col-span-1 space-y-6">
            <Card className="p-6 bg-slate-900/50 border-white/5 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-white">Your Files</h2>
                <Button onClick={fetchFiles} variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-white">
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>
              
              <div className="relative group mb-6">
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  onChange={(e) => e.target.files && uploadFile(e.target.files[0])}
                />
                <label 
                  htmlFor="file-upload"
                  className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-indigo-500/30 rounded-xl bg-indigo-500/5 hover:bg-indigo-500/10 transition-colors cursor-pointer group-hover:border-indigo-400/50"
                >
                  {uploading ? (
                    <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                      <RefreshCw className="w-6 h-6 text-indigo-400" />
                    </motion.div>
                  ) : (
                    <>
                      <UploadCloud className="w-8 h-8 text-indigo-400 mb-2 group-hover:scale-110 transition-transform" />
                      <span className="text-sm text-indigo-300 font-medium">Click to upload</span>
                    </>
                  )}
                </label>
              </div>

              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
                <AnimatePresence>
                  {files.map(file => (
                    <motion.div
                      key={file.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      whileHover={{ scale: 1.02 }}
                    >
                      <Card
                        className={`p-4 cursor-pointer transition-all border ${
                          selectedFile?.id === file.id 
                            ? 'bg-indigo-600/20 border-indigo-500/50 shadow-[0_0_15px_rgba(99,102,241,0.1)]' 
                            : 'bg-slate-800/50 border-white/5 hover:bg-slate-800'
                        }`}
                        onClick={() => {
                          setSelectedFile(file)
                          setSummary('')
                          setMessages([])
                        }}
                      >
                        <div className="flex items-start gap-3">
                          <div className="mt-1">{getFileIcon(file.type)}</div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-sm text-slate-200 truncate">{file.name}</p>
                            <p className="text-xs text-slate-500 mt-1 capitalize flex items-center gap-1">
                              <span className={`w-1.5 h-1.5 rounded-full ${file.status === 'ready' ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
                              {file.status}
                            </p>
                          </div>
                        </div>
                        
                        {file.status === 'uploaded' && selectedFile?.id === file.id && (
                          <Button 
                            onClick={(e) => { e.stopPropagation(); processFile(file.id); }} 
                            size="sm" 
                            className="mt-3 w-full bg-indigo-600 hover:bg-indigo-500 text-white"
                          >
                            Process File
                          </Button>
                        )}
                        {file.status === 'ready' && selectedFile?.id === file.id && !summary && (
                          <Button 
                            onClick={(e) => { e.stopPropagation(); getSummary(file.id); }} 
                            size="sm" 
                            variant="secondary"
                            className="mt-3 w-full bg-slate-700 hover:bg-slate-600 text-white border-0"
                            disabled={loading}
                          >
                            {loading ? 'Generating...' : 'Generate Summary'}
                          </Button>
                        )}
                      </Card>
                    </motion.div>
                  ))}
                </AnimatePresence>
                {files.length === 0 && (
                  <div className="text-center py-8 text-slate-500 text-sm">
                    No files uploaded yet.
                  </div>
                )}
              </div>
            </Card>
          </div>

          {/* Main Panel: Chat & Summary */}
          <div className="lg:col-span-2 flex flex-col h-[calc(100vh-8rem)]">
            {/* Summary Area */}
            <AnimatePresence>
              {summary && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-6 overflow-hidden"
                >
                  <Card className="p-6 bg-gradient-to-br from-indigo-900/30 to-purple-900/30 border-indigo-500/20">
                    <h2 className="text-sm font-semibold text-indigo-300 mb-3 uppercase tracking-wider flex items-center gap-2">
                      <FileText className="w-4 h-4" /> AI Summary
                    </h2>
                    <p className="text-slate-300 text-sm leading-relaxed whitespace-pre-wrap">{summary}</p>

                    {/* Navigation-enabled summary panel (uses timestamp ranges from chat metadata) */}
                    <div className="mt-4">
                      <h3 className="text-xs font-medium text-indigo-200 uppercase tracking-wider mb-2">
                        Jump to segments
                      </h3>

                      {(() => {
                        const allRanges = messages.flatMap((m) => m.timestamp_ranges || [])
                        const uniq: Array<{ start_time: number; end_time: number }> = []
                        const seen = new Set<string>()

                        for (const r of allRanges) {
                          const key = `${r.start_time}-${r.end_time}`
                          if (seen.has(key)) continue
                          seen.add(key)
                          uniq.push({ start_time: r.start_time, end_time: r.end_time })
                        }

                        const limited = uniq.slice(0, 12)
                        if (limited.length === 0) return null

                        return (
                          <div className="flex flex-wrap gap-2">
                            {limited.map((r, idx) => (
                              <button
                                key={idx}
                                type="button"
                                onClick={() => jumpToTime(r.start_time)}
                                className="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded transition-all bg-indigo-500/10 text-indigo-200 border border-indigo-500/30 hover:bg-indigo-500/20"
                                title={`Jump to ${r.start_time}s`}
                              >
                                {Math.floor(r.start_time / 60)}m
                                {Math.floor(r.start_time % 60)
                                  .toString()
                                  .padStart(2, '0')}
                              </button>
                            ))}
                          </div>
                        )
                      })()}
                    </div>
                  </Card>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Chat Area */}
            <Card className="flex-1 flex flex-col bg-slate-900/50 border-white/5 backdrop-blur-sm overflow-hidden">
              <div className="p-4 border-b border-white/5 bg-slate-900/80">
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-indigo-400" />
                  AI Assistant
                </h2>
                {selectedFile && (
                  <p className="text-xs text-slate-400 mt-1">Asking questions about: <span className="text-slate-300 font-medium">{selectedFile.name}</span></p>
                )}
              </div>
              
              <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {!selectedFile ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
                    <MessageSquare className="w-12 h-12 text-slate-700" />
                    <p>Select a processed file to start chatting</p>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-500">
                    <p>Ask anything about this document.</p>
                    <div className="flex gap-2 mt-4 text-xs">
                      <span className="px-3 py-1 bg-slate-800 rounded-full cursor-pointer hover:bg-slate-700 transition" onClick={() => setQuestion("What are the key takeaways?")}>What are the key takeaways?</span>
                      <span className="px-3 py-1 bg-slate-800 rounded-full cursor-pointer hover:bg-slate-700 transition" onClick={() => setQuestion("Summarize this in bullet points.")}>Summarize in bullets</span>
                    </div>
                  </div>
                ) : (
                  messages.map((msg, idx) => (
                    <motion.div 
                      key={idx} 
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="space-y-4"
                    >
                      {/* User Message */}
                      <div className="flex justify-end">
                        <div className="bg-indigo-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm max-w-[80%] shadow-md">
                          <p className="text-sm">{msg.question}</p>
                        </div>
                      </div>
                      
                      {/* AI Message */}
                      <div className="flex justify-start">
                        <div className={`px-4 py-3 rounded-2xl rounded-tl-sm max-w-[90%] shadow-md border ${
                          msg.error
                            ? 'bg-red-900/20 border-red-500/30 text-red-200'
                            : 'bg-slate-800 text-slate-200 border-slate-700'
                        }`}>
                          {msg.error ? (
                            <div className="flex items-start gap-2">
                              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                              <p className="text-sm">{msg.error}</p>
                            </div>
                          ) : msg.isStreaming && !msg.answer ? (
                            <div className="flex items-center gap-2 h-5">
                              <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                              >
                                <div className="w-1.5 h-1.5 bg-indigo-400 rounded-full" />
                              </motion.div>
                              <span className="text-sm text-slate-400">Thinking...</span>
                            </div>
                          ) : (
                            <>
                              <div className="text-sm leading-relaxed whitespace-pre-wrap">{msg.answer}</div>
                              {msg.isStreaming && (
                                <motion.span
                                  animate={{ opacity: [0, 1] }}
                                  transition={{ repeat: Infinity, duration: 1 }}
                                  className="inline-block ml-1 w-1.5 h-5 bg-indigo-400 rounded"
                                />
                              )}
                            </>
                          )}

                          {/* Timestamp Ranges */}
                          {!msg.error && msg.timestamp_ranges && msg.timestamp_ranges.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-700 flex flex-wrap gap-2">
                              {msg.timestamp_ranges.map((range, i) => (
                                <TimestampButton
                                  key={i}
                                  startTime={range.start_time}
                                  endTime={range.end_time}
                                  onPlay={jumpToTime}
                                  variant="compact"
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-4 bg-slate-900 border-t border-white/5">
                <div className="relative flex items-center">
                  <Input
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder={selectedFile?.status === 'ready' ? "Ask a question..." : "Process file to ask questions"}
                    disabled={!selectedFile || selectedFile.status !== 'ready'}
                    onKeyPress={(e) => e.key === 'Enter' && askQuestion()}
                    className="flex-1 bg-slate-800 border-slate-700 text-white placeholder:text-slate-500 pr-12 focus-visible:ring-indigo-500 h-12 rounded-xl"
                  />
                  <Button 
                    onClick={askQuestion} 
                    disabled={!selectedFile || selectedFile.status !== 'ready' || !question.trim()}
                    size="icon"
                    className="absolute right-1.5 h-9 w-9 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {/* Right Panel: Media Player */}
          <div className="lg:col-span-1">
            <Card className="p-6 bg-slate-900/50 border-white/5 backdrop-blur-sm sticky top-24">
              <h2 className="text-lg font-semibold text-white mb-4">Media Player</h2>
              {selectedFile ? (
                <div className="space-y-4">
                  {(selectedFile.type.startsWith('audio/') || selectedFile.type.startsWith('video/')) && (
                    <MediaPlayer
                      ref={playerRef}
                      src={`http://localhost:8000${selectedFile.url}`}
                      type={selectedFile.type}
                      fileName={selectedFile.name}
                    />
                  )}
                  {!selectedFile.type.startsWith('audio/') && !selectedFile.type.startsWith('video/') && (
                    <div className="flex flex-col items-center justify-center p-8 bg-slate-800/50 rounded-xl border border-dashed border-slate-700 text-center">
                      <FileText className="w-10 h-10 text-slate-600 mb-3" />
                      <p className="text-sm text-slate-400">No playback available</p>
                      <p className="text-xs text-slate-500 mt-1">Text document selected</p>
                    </div>
                  )}
                  
                  <div className="bg-slate-800/50 p-4 rounded-xl border border-slate-700 mt-4">
                    <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">File Info</h3>
                    <div className="space-y-2 text-sm text-slate-300">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Name</span>
                        <span className="truncate ml-4 max-w-[150px]">{selectedFile.name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Type</span>
                        <span>{selectedFile.type.split('/')[1]?.toUpperCase() || 'Document'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Status</span>
                        <span className="capitalize text-emerald-400">{selectedFile.status}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center p-8 bg-slate-800/30 rounded-xl border border-dashed border-slate-700 text-center min-h-[200px]">
                  <Cpu className="w-10 h-10 text-slate-700 mb-3" />
                  <p className="text-sm text-slate-400">No media selected</p>
                  <p className="text-xs text-slate-500 mt-1">Select a file to view details</p>
                </div>
              )}
            </Card>
          </div>
        </div>
      </div>
      
      {/* Required for dynamic MessageSquare import which was missing in original page */}
      <style dangerouslySetInnerHTML={{__html: `
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.02);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}} />
    </div>
  )
}
