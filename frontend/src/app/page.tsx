'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { v4 as uuidv4 } from 'uuid'
import { FileText, Cpu, MessageSquare, Clock, FileCheck, Shield } from 'lucide-react'

export default function Home() {
  const [loading, setLoading] = useState(false)
  const router = useRouter()

  const handleGetStarted = () => {
    setLoading(true)
    let sessionId = localStorage.getItem('sessionId')
    if (!sessionId) {
      sessionId = uuidv4()
      localStorage.setItem('sessionId', sessionId)
    }
    router.push('/dashboard')
  }

  const features = [
    { icon: <FileText className="w-8 h-8 text-blue-500" />, title: 'File Upload', desc: 'Upload PDFs, audio files, and videos securely to our platform.' },
    { icon: <Cpu className="w-8 h-8 text-purple-500" />, title: 'AI Processing', desc: 'Automatic transcription and content analysis using advanced AI.' },
    { icon: <MessageSquare className="w-8 h-8 text-indigo-500" />, title: 'Smart Q&A', desc: 'Ask questions in natural language and get precise answers.' },
    { icon: <Clock className="w-8 h-8 text-pink-500" />, title: 'Timestamp Navigation', desc: 'Jump directly to relevant parts of your media files.' },
    { icon: <FileCheck className="w-8 h-8 text-green-500" />, title: 'Summary Generation', desc: 'Get concise summaries of your documents and transcripts.' },
    { icon: <Shield className="w-8 h-8 text-slate-500" />, title: 'Secure & Private', desc: 'Your files are processed securely with enterprise-grade encryption.' }
  ]

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 selection:bg-indigo-500/30">
      {/* Background gradients */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-indigo-600/20 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-600/20 blur-[120px]" />
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/10 bg-black/20 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <FileText className="w-5 h-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-400 to-purple-400">DocPulse</h1>
            </div>
            <nav className="hidden md:flex space-x-8">
              <a href="#features" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">Features</a>
              <a href="#about" className="text-sm font-medium text-slate-300 hover:text-white transition-colors">About</a>
            </nav>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className="text-center space-y-8"
        >
          <div className="inline-flex items-center px-4 py-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-300 text-sm font-medium mb-8">
            <span className="flex h-2 w-2 rounded-full bg-indigo-500 mr-2 animate-pulse"></span>
            Powered by Gemini AI
          </div>
          
          <h2 className="text-5xl md:text-7xl font-extrabold tracking-tight">
            Chat with your <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400">
              Documents & Media
            </span>
          </h2>
          
          <p className="max-w-2xl mx-auto text-lg md:text-xl text-slate-400">
            Upload PDFs, audio, and video files. Ask questions and get instant, intelligent answers without needing to create an account.
          </p>
          
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-8">
            <Button 
              size="lg" 
              onClick={handleGetStarted}
              disabled={loading}
              className="w-full sm:w-auto text-lg px-8 py-6 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-lg shadow-indigo-500/25 border-0 transition-all hover:scale-105"
            >
              {loading ? 'Starting session...' : 'Start Exploring Instantly'}
            </Button>
          </div>
        </motion.div>

        {/* Features Section */}
        <div id="features" className="mt-32">
          <div className="text-center mb-16">
            <h3 className="text-3xl font-bold">Powerful Features</h3>
            <p className="mt-4 text-slate-400">Everything you need to extract knowledge from your files.</p>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                viewport={{ once: true }}
              >
                <Card className="p-8 h-full bg-white/5 border-white/10 backdrop-blur-sm hover:bg-white/10 transition-colors">
                  <div className="mb-6 p-4 rounded-2xl bg-black/20 inline-block">
                    {feature.icon}
                  </div>
                  <h4 className="text-xl font-semibold mb-3 text-white">{feature.title}</h4>
                  <p className="text-slate-400 leading-relaxed">
                    {feature.desc}
                  </p>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/10 bg-black/20 mt-24">
        <div className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8 text-center text-slate-500">
          <p>&copy; {new Date().getFullYear()} DocPulse. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
