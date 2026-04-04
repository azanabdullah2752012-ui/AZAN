import React from 'react'
import { motion } from 'framer-motion'

function StatusDot({ label, ok }) {
  return (
    <div className="flex items-center gap-1.5">
      <motion.span
        className="w-2 h-2 rounded-full"
        style={{ background: ok ? '#22c55e' : '#ef4444' }}
        animate={{ scale: ok ? [1, 1.3, 1] : 1 }}
        transition={{ duration: 2, repeat: Infinity }}
      />
      <span className="font-mono text-[10px] text-slate-500 uppercase tracking-wider">{label}</span>
    </div>
  )
}

export default function TopBar({ status, model, setModel, uptime }) {
  const online = !!status?.orchestrator

  return (
    <div className="glass scanline flex items-center gap-4 px-4 py-2 shrink-0" style={{ borderRadius: 0, borderLeft: 0, borderRight: 0, borderTop: 0 }}>
      {/* Brand */}
      <div className="flex items-center gap-2 mr-4">
        <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
          <polygon points="16,2 28,9 28,23 16,30 4,23 4,9" stroke="#00f2ff" strokeWidth="1.5" fill="none" />
          <circle cx="16" cy="16" r="4" fill="#00f2ff" opacity="0.8" />
        </svg>
        <span className="font-hud text-sm font-bold tracking-[0.25em] text-jarvis-cyan glow-text">
          J.A.R.V.I.S
        </span>
        <span className="font-mono text-[9px] text-slate-600">OS v16.0</span>
      </div>

      {/* Status dots */}
      <div className="flex items-center gap-4">
        <StatusDot label="Core"   ok={online} />
        <StatusDot label="Ollama" ok={!!status?.system?.ollama} />
        <StatusDot label="Memory" ok={true} />
      </div>

      <div className="h-5 w-px bg-jarvis-border mx-2" />

      {/* Model selector */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] text-slate-600 uppercase">Model</span>
        <span className="font-mono text-xs text-jarvis-cyan border border-jarvis-border px-2 py-0.5 rounded">
          {model}
        </span>
      </div>

      {/* Right side */}
      <div className="ml-auto flex items-center gap-4">
        <div className="font-mono text-[10px] text-slate-600">
          UPTIME <span className="text-jarvis-cyan">{uptime}</span>
        </div>
        <div className="font-mono text-[10px] text-slate-600">
          {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
    </div>
  )
}
