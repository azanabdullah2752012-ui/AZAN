import React from 'react'
import { motion } from 'framer-motion'

function Gauge({ label, value, max = 100, color = '#00f2ff' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">{label}</span>
        <span className="font-mono text-xs" style={{ color }}>{typeof value === 'number' ? value.toFixed(1) : value}%</span>
      </div>
      <div className="h-1 bg-white/5 rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 6px ${color}80`, width: `${pct}%` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

function Row({ label, value, indicator }) {
  const dot = indicator === 'ok' ? '#22c55e' : indicator === 'warn' ? '#eab308' : indicator === 'error' ? '#ef4444' : '#00f2ff'
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
      <span className="font-mono text-[10px] text-slate-500 uppercase tracking-widest">{label}</span>
      <div className="flex items-center gap-1.5">
        {indicator && <span className="w-1.5 h-1.5 rounded-full" style={{ background: dot, boxShadow: `0 0 4px ${dot}` }} />}
        <span className="font-mono text-xs text-slate-300">{value ?? '–'}</span>
      </div>
    </div>
  )
}

export default function TelemetryPanel({ status }) {
  const sys = status?.system || {}
  const ram = sys.ram || {}

  const workerStatus = status?.continuous_learner === 'running' ? 'ok' : 'warn'
  const orchStatus  = status?.orchestrator === 'ready' ? 'ok' : 'warn'

  return (
    <div className="glass scanline corner-tl corner-br relative p-3 flex flex-col h-full overflow-hidden">
      <p className="font-hud text-[10px] tracking-[0.3em] uppercase text-jarvis-cyan/60 mb-3">
        SYS TELEMETRY
      </p>

      <Gauge label="CPU" value={sys.cpu_percent ?? 0} color="#00f2ff" />
      <Gauge label="RAM" value={ram.percent ?? 0}     color="#7c3aed" />

      <div className="mt-auto">
        <Row label="LLM Engine"     value={sys.ollama ?? 'Checking…'} indicator={sys.ollama ? 'ok' : 'warn'} />
        <Row label="Orchestrator"   value={status?.orchestrator ?? '–'} indicator={orchStatus}  />
        <Row label="BG Learner"     value={status?.continuous_learner ?? '–'} indicator={workerStatus} />
        <Row label="Automation"     value={status?.automation_engine ?? '–'} indicator={status?.automation_engine === 'active' ? 'ok' : 'warn'} />
        <Row label="Active App"     value={status?.active_app ?? 'None'} />
        <Row label="Last Action"    value={status?.last_action ?? 'System Idle'} />
        <Row label="Ollama"         value={sys.ollama ?? '–'} />
      </div>
    </div>
  )
}
