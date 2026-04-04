import React from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

const TOOL_COLORS = {
  web_search:       'text-blue-400  border-blue-400/40  bg-blue-400/10',
  code_runner:      'text-green-400 border-green-400/40 bg-green-400/10',
  shell:            'text-green-400 border-green-400/40 bg-green-400/10',
  file_manager:     'text-yellow-400 border-yellow-400/40 bg-yellow-400/10',
  computer_control: 'text-red-400   border-red-400/40   bg-red-400/10',
  spotify:          'text-green-300 border-green-300/40 bg-green-300/10',
  system_control:   'text-red-300   border-red-300/40   bg-red-300/10',
  apple_messages:   'text-blue-300  border-blue-300/40  bg-blue-300/10',
  whatsapp:         'text-green-400 border-green-400/40 bg-green-400/10',
  apple_calendar:   'text-purple-400 border-purple-400/40 bg-purple-400/10',
  default:          'text-cyan-400  border-cyan-400/40  bg-cyan-400/10',
}

function toolColor(name) {
  return TOOL_COLORS[name] || TOOL_COLORS.default
}

export function ActionCard({ step }) {
  const colors = toolColor(step.tool)
  const hasObs = step.obs?.trim()
  const hasErr = step.obs?.toLowerCase().includes('error')

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0,  scale: 1 }}
      transition={{ duration: 0.3 }}
      className="glass corner-tl corner-br scanline relative p-3 mb-2 overflow-hidden"
    >
      {/* Tool badge */}
      <div className="flex items-center gap-2 mb-2">
        <span className="text-xs font-mono text-jarvis-cyan opacity-50">⚙ ACTION</span>
        <span className={clsx('text-xs font-mono border px-2 py-0.5 rounded', colors)}>
          {step.tool}
        </span>
      </div>

      {/* Input */}
      {step.input?.trim() && (
        <div className="mb-2">
          <p className="text-xs text-jarvis-cyan/50 font-mono mb-0.5">📥 INPUT</p>
          <p className="text-xs text-slate-300 font-mono bg-black/30 rounded px-2 py-1 break-all">
            {step.input.trim().slice(0, 300)}
          </p>
        </div>
      )}

      {/* Observation */}
      {hasObs && (
        <div>
          <p className={clsx('text-xs font-mono mb-0.5', hasErr ? 'text-red-400' : 'text-jarvis-cyan/50')}>
            {hasErr ? '🔴 ERROR' : '📡 OBSERVATION'}
          </p>
          <pre className={clsx('text-xs font-mono bg-black/40 rounded px-2 py-1 overflow-x-auto max-h-28 whitespace-pre-wrap break-all', hasErr ? 'text-red-300' : 'text-slate-300')}>
            {step.obs.trim().slice(0, 800)}
          </pre>
        </div>
      )}

      {/* Corner glow */}
      <div className="absolute top-0 right-0 w-12 h-12 rounded-bl-full"
           style={{ background: `radial-gradient(circle, rgba(0,242,255,0.06) 0%, transparent 80%)` }} />
    </motion.div>
  )
}

export function UserCard({ step }) {
  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-start gap-2 mb-2"
    >
      <span className="text-jarvis-cyan/40 text-xs font-mono mt-1 shrink-0">▶</span>
      <p className="text-sm font-mono text-slate-200 break-all">{step.text}</p>
    </motion.div>
  )
}

export function AnswerCard({ step }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="glass p-3 mb-2 border-l-2 border-jarvis-cyan/50"
    >
      <p className="text-xs font-mono text-jarvis-cyan/50 mb-1">🧠 JARVIS RESPONSE</p>
      <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{step.text}</p>
    </motion.div>
  )
}

export function ErrorCard({ step }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="glass p-3 mb-2 border border-red-500/40 bg-red-500/5"
    >
      <p className="text-xs font-mono text-red-400 mb-1">🔴 SYSTEM ERROR</p>
      <p className="text-xs text-red-300 font-mono">{step.text}</p>
    </motion.div>
  )
}

export function ThinkingCard() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{ duration: 1.5, repeat: Infinity }}
      className="flex items-center gap-2 py-2 mb-2"
    >
      <div className="w-1.5 h-1.5 bg-jarvis-cyan rounded-full" />
      <div className="w-1.5 h-1.5 bg-jarvis-cyan rounded-full" style={{ animationDelay: '0.2s' }} />
      <div className="w-1.5 h-1.5 bg-jarvis-cyan rounded-full" style={{ animationDelay: '0.4s' }} />
      <span className="text-xs font-mono text-jarvis-cyan/60 ml-1">REASONING…</span>
    </motion.div>
  )
}
