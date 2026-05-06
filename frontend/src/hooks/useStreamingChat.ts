/**
 * Custom React Hook for streaming chat
 * Manages SSE connection lifecycle and message accumulation
 */

import { useCallback, useRef } from 'react'
import {
  StreamingChatClient,
  fallbackNonStreamingChat,
  type StreamEventHandlers
} from '@/utils/streamingClient'

export interface TimestampRange {
  start_time: number
  end_time: number
  chunk_index?: number
}

export interface StreamingMessage {
  id: string
  question: string
  answer: string
  timestamp_ranges: TimestampRange[]
  source_file?: string
  isStreaming: boolean
  error?: string
}

export interface UseStreamingChatOptions {
  onMessageStart?: (messageId: string) => void
  onTokenReceived?: (token: string) => void
  onMetadataReceived?: (metadata: {
    timestamp_ranges?: TimestampRange[]
    source_file?: string
  }) => void
  onMessageComplete?: (message: StreamingMessage) => void
  onError?: (error: string) => void
}

export function useStreamingChat(options: UseStreamingChatOptions = {}) {
  const clientRef = useRef<StreamingChatClient | null>(null)
  const messageBuilderRef = useRef<{
    id: string
    question: string
    answer: string
    timestamp_ranges: TimestampRange[]
    source_file?: string
  } | null>(null)

  /**
   * Start streaming a chat response
   */
  const stream = useCallback(
    async (
      fileId: string,
      question: string,
      sessionId: string,
      messageId: string
    ) => {
      // Initialize message builder
      messageBuilderRef.current = {
        id: messageId,
        question,
        answer: '',
        timestamp_ranges: [],
        source_file: undefined
      }

      options.onMessageStart?.(messageId)

      // Create client
      clientRef.current = new StreamingChatClient()

      // Define handlers
      const cleanup = () => {
        if (clientRef.current) {
          clientRef.current.disconnect()
          clientRef.current = null
        }
        messageBuilderRef.current = null
      }

      const handlers: StreamEventHandlers = {
        onToken: (token: string) => {
          if (messageBuilderRef.current) {
            messageBuilderRef.current.answer += token
            options.onTokenReceived?.(token)
          }
        },
        onMetadata: (metadata) => {
          if (messageBuilderRef.current) {
            messageBuilderRef.current.timestamp_ranges =
              metadata.timestamp_ranges || []
            messageBuilderRef.current.source_file = metadata.source_file
            options.onMetadataReceived?.(metadata)
          }
        },
        onError: (error: string) => {
          options.onError?.(error)
          if (messageBuilderRef.current) {
            options.onMessageComplete?.({
              ...messageBuilderRef.current,
              isStreaming: false,
              error
            })
          }
        },
        onDone: () => {
          if (messageBuilderRef.current) {
            options.onMessageComplete?.({
              ...messageBuilderRef.current,
              isStreaming: false
            })
          }
          cleanup()
        }
      }

      try {
        // Try streaming first
        clientRef.current.connect(fileId, question, sessionId, handlers)
      } catch (error) {
        console.warn(
          'Streaming connection failed, falling back to non-streaming',
          error
        )
        // Fallback to non-streaming
        try {
          await fallbackNonStreamingChat(
            fileId,
            question,
            sessionId,
            handlers
          )
        } catch (fallbackError) {
          handlers.onError(
            fallbackError instanceof Error
              ? fallbackError.message
              : 'Failed to get response'
          )
        }
      }
    },
    [options]
  )

  /**
   * Cancel ongoing stream
   */
  const cancel = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.disconnect()
      clientRef.current = null
    }
  }, [])

  /**
   * Check if currently streaming
   */
  const isStreaming = useCallback(() => {
    return clientRef.current?.isConnected() ?? false
  }, [])

  return {
    stream,
    cancel,
    isStreaming
  }
}
