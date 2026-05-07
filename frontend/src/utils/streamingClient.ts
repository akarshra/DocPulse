/**
 * Server-Sent Events (SSE) Client for streaming chat responses
 * Handles EventSource connections and event parsing
 */

export interface StreamEventHandlers {
  onToken: (token: string) => void
  onMetadata: (metadata: {
    timestamp_ranges?: Array<{ start_time: number; end_time: number }>
    source_file?: string
  }) => void
  onError: (error: string) => void
  onDone: () => void
}

export class StreamingChatClient {
  private eventSource: EventSource | null = null
  private abortController: AbortController | null = null

  /**
   * Connect to streaming chat endpoint and listen for events
   */
  connect(
    fileId: string,
    question: string,
    sessionId: string,
    handlers: StreamEventHandlers
  ): void {
    // Build URL with query parameters
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://docpulse-6o2j.onrender.com'
    const url = new URL(`${apiUrl}/api/chat/stream`)
    url.searchParams.append('file_id', fileId)
    url.searchParams.append('question', question)
    // EventSource can't set custom headers, so pass session_id via query param as well.
    url.searchParams.append('session_id', sessionId)


    // Create EventSource
    this.eventSource = new EventSource(url.toString(), {
      // Note: withCredentials not directly settable on EventSource,
      // but session ID is in query params
    })

    // Add X-Session-ID header (won't work with EventSource query params)
    // This is a limitation of EventSource - it doesn't support custom headers
    // Workaround: session_id passed via query param above

    // Handle different event types
    this.eventSource.addEventListener('token', (event: Event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        handlers.onToken(data.token)
      } catch (e) {
        console.error('Failed to parse token event:', e)
        handlers.onError('Failed to parse token event')
      }
    })

    this.eventSource.addEventListener('metadata', (event: Event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        handlers.onMetadata(data)
      } catch (e) {
        console.error('Failed to parse metadata event:', e)
        handlers.onError('Failed to parse metadata')
      }
    })

    this.eventSource.addEventListener('error', (event: Event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data)
        handlers.onError(data.error || 'Unknown error')
      } catch { 

        // Check EventSource readyState for connection errors
        if (this.eventSource?.readyState === EventSource.CLOSED) {
          handlers.onError('Connection closed')
        } else {
          handlers.onError('Connection error')
        }
      }
      this.disconnect()
    })

    this.eventSource.addEventListener('done', () => {
      handlers.onDone()
      this.disconnect()
    })

    // Handle connection open
    this.eventSource.onopen = () => {
      console.log('Connected to streaming chat')
    }

    // Handle general errors
    this.eventSource.onerror = () => {
      if (this.eventSource?.readyState === EventSource.CLOSED) {
        handlers.onError('Connection closed unexpectedly')
      } else {
        handlers.onError('Connection error')
      }
      this.disconnect()
    }
  }

  /**
   * Disconnect from streaming endpoint
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
    if (this.abortController) {
      this.abortController.abort()
      this.abortController = null
    }
  }

  /**
   * Check if currently connected
   */
  isConnected(): boolean {
    return (
      this.eventSource !== null &&
      this.eventSource.readyState === EventSource.OPEN
    )
  }
}

/**
 * Fallback to non-streaming endpoint if SSE fails
 */
export async function fallbackNonStreamingChat(
  fileId: string,
  question: string,
  sessionId: string,
  handlers: StreamEventHandlers
): Promise<void> {
  try {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://docpulse-6o2j.onrender.com'
    const response = await fetch(`${apiUrl}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-ID': sessionId
      },
      body: JSON.stringify({
        file_id: fileId,
        question: question
      })
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const data = await response.json()

    // Emit entire answer as single token (non-streaming behavior)
    handlers.onToken(data.answer)

    // Send metadata
    handlers.onMetadata({
      timestamp_ranges: data.timestamp_ranges,
      source_file: data.source_file
    })

    // Signal completion
    handlers.onDone()
  } catch (error) {
    handlers.onError(
      error instanceof Error ? error.message : 'Unknown error'
    )
  }
}
