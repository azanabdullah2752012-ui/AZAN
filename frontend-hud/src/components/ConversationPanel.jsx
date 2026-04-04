import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ActionCard, UserCard, AnswerCard, ErrorCard, ThinkingCard } from './StepCards'

export default function ConversationPanel({ steps, jarvisState }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [steps])

  return (
    <div className="glass scanline corner-tl corner-br relative flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-jarvis-border shrink-0">
        <span className="w-1.5 h-1.5 rounded-full bg-jarvis-cyan animate-pulse-slow" />
        <span className="font-mono text-[10px] tracking-widest uppercase text-jarvis-cyan/60">
          ReAct Reasoning Stream
        </span>
        <span className="ml-auto font-mono text-[9px] text-slate-600">{steps.length} operations</span>
      </div>

      {/* Steps */}
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
        <AnimatePresence initial={false}>
          {steps.map((step, i) => {
            if (step.type === 'user')   return <UserCard   key={i} step={step} />
            if (step.type === 'action') return <ActionCard key={i} step={step} />
            if (step.type === 'answer') return <AnswerCard key={i} step={step} />
            if (step.type === 'error')  return <ErrorCard  key={i} step={step} />
            return null
          })}
        </AnimatePresence>

        {jarvisState !== 'idle' && <ThinkingCard />}
        <div ref={bottomRef} />
      </div>

      {/* Bottom glow */}
      <div className="h-8 shrink-0 pointer-events-none"
           style={{ background: 'linear-gradient(to top, rgba(3,7,18,0.9), transparent)' }} />
    </div>
  )
}
