export function runAgent(hypothesis, callbacks = {}) {
  const controller = new AbortController()

  const promise = readAgentStream(hypothesis, callbacks, controller.signal)

  return {
    abort: () => controller.abort(),
    promise,
  }
}

async function readAgentStream(hypothesis, callbacks, signal) {
  try {
    const response = await fetch('/api/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ hypothesis }),
      signal,
    })

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status} ${response.statusText}`.trim())
    }

    if (!response.body) {
      throw new Error('Backend response did not include a stream')
    }

    await parseSseStream(response.body, callbacks, signal)
  } catch (error) {
    if (error?.name === 'AbortError' || signal.aborted) {
      return
    }
    callbacks.onError?.(error)
  }
}

async function parseSseStream(body, callbacks, signal) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let eventName = ''
  let dataLines = []

  function dispatchEvent() {
    if (dataLines.length === 0) {
      eventName = ''
      return
    }

    const rawData = dataLines.join('\n')
    eventName = eventName || 'message'
    dataLines = []

    let payload
    try {
      payload = JSON.parse(rawData)
    } catch (error) {
      callbacks.onError?.(new Error(`Invalid SSE payload: ${error.message}`))
      return
    }

    const type = payload.type || eventName
    if (type === 'iteration') {
      callbacks.onIteration?.(payload)
    } else if (type === 'complete') {
      const decisionLog = payload.decisionLog || {}
      callbacks.onComplete?.({
        finalCandidate: payload.finalCandidate || null,
        decisionLog,
        portfolio: decisionLog.portfolio || [],
        ineligible: decisionLog.ineligible || [],
        testQueue: decisionLog.test_queue || decisionLog.testQueue || [],
        constraints: decisionLog.constraints || {},
        provenanceTree: decisionLog.provenance_tree || decisionLog.provenanceTree || null,
        terminalTranscript: payload.terminalTranscript || '',
      })
    } else if (type === 'error') {
      callbacks.onError?.(new Error(payload.message || 'Agent stream reported an error'))
    }

    eventName = ''
  }

  while (!signal.aborted) {
    const { value, done } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split(/\r?\n/)
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line === '') {
        dispatchEvent()
      } else if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }
  }

  buffer += decoder.decode()
  if (buffer.trim()) {
    for (const line of buffer.split(/\r?\n/)) {
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }
  }
  dispatchEvent()
}
