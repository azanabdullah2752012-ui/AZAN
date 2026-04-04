import React, { useState, useEffect, useCallback, useRef } from 'react'
import './index.css'
import HUD from './components/HUD'

export default function App() {
  const [status, setStatus] = useState({ orchestrator: '–', system: {}, continuous_learner: '–' })
  const [model, setModel] = useState('llama3')
  const [steps, setSteps] = useState([])          // ReAct step cards
  const [jarvisState, setJarvisState] = useState('idle') // idle | thinking | executing | speaking
  const [memory, setMemory]   = useState([])
  const [uptime, setUptime]   = useState(0)
  const [sessionId] = useState('sess_' + Date.now())

  // Poll system status
  useEffect(() => {
    const poll = async () => {
      try {
        const d = await fetch('/api/jarvis/status').then(r => r.json())
        setStatus(d)
      } catch (_) {}
    }
    poll()
    const id = setInterval(poll, 8000)
    return () => clearInterval(id)
  }, [])

  // Uptime clock
  useEffect(() => {
    const id = setInterval(() => setUptime(u => u + 1), 1000)
    return () => clearInterval(id)
  }, [])

  const formatUptime = (s) => {
    const h = String(Math.floor(s / 3600)).padStart(2, '0')
    const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
    const sec = String(s % 60).padStart(2, '0')
    return `${h}:${m}:${sec}`
  }

  const sendCommand = useCallback(async (prompt) => {
    setJarvisState('thinking')
    setSteps(prev => [...prev, { type: 'user', text: prompt, ts: Date.now() }])

    try {
      const res = await fetch('/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, session_id: sessionId, model })
      })

      if (!res.ok) throw new Error('Stream error')

      const reader = res.body.getReader()
      const dec    = new TextDecoder()
      let   full   = ''
      let   currentStep = null

      const flushStep = () => {
        if (currentStep) {
          setSteps(prev => [...prev, currentStep])
          currentStep = null
        }
      }

      outerLoop: while (true) {
        const { done, value } = await reader.read()
        if (done) break

        for (const line of dec.decode(value).split('\n')) {
          if (!line.startsWith('data: ')) continue
          try {
            const dd = JSON.parse(line.slice(6))
            if (dd.done) break outerLoop

            if (dd.token) {
              const t = dd.token

              // Detect tool execution markers
              const toolMatch = t.match(/\*\(Executing Tool: `(.+?)`\)\*/)
              if (toolMatch) {
                flushStep()
                setJarvisState('executing')
                currentStep = { type: 'action', tool: toolMatch[1], input: '', obs: '', ts: Date.now() }
                continue
              }

              // Detect observation
              if (t.includes('**Observation:**')) {
                setJarvisState('thinking')
                if (currentStep) currentStep.observing = true
                continue
              }

              if (currentStep?.observing) {
                currentStep.obs += t
              } else if (currentStep) {
                currentStep.input += t
              } else {
                full += t
              }
            }
          } catch (_) {}
        }
      }

      flushStep()
      if (full.trim()) {
        setSteps(prev => [...prev, { type: 'answer', text: full, ts: Date.now() }])
      }
    } catch (e) {
      setSteps(prev => [...prev, { type: 'error', text: e.message, ts: Date.now() }])
    } finally {
      setJarvisState('idle')
    }
  }, [sessionId, model])

  return (
    <HUD
      status={status}
      model={model}
      setModel={setModel}
      steps={steps}
      jarvisState={jarvisState}
      memory={memory}
      uptime={formatUptime(uptime)}
      onCommand={sendCommand}
    />
  )
}
