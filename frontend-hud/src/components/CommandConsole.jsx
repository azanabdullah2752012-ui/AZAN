import React, { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'

export default function CommandConsole({ onCommand, jarvisState }) {
  const [value, setValue] = useState('')
  const [history, setHistory] = useState([])
  const [histIdx, setHistIdx] = useState(-1)
  const inputRef = useRef(null)

  useEffect(() => { inputRef.current?.focus() }, [])

  const submit = () => {
    const cmd = value.trim()
    if (!cmd) return
    setHistory(h => [cmd, ...h.slice(0, 49)])
    setHistIdx(-1)
    setValue('')
    onCommand(cmd)
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter')     { e.preventDefault(); submit(); return }
    if (e.key === 'ArrowUp')   { e.preventDefault(); const ni = Math.min(histIdx + 1, history.length - 1); setHistIdx(ni); setValue(history[ni] ?? ''); return }
    if (e.key === 'ArrowDown') { e.preventDefault(); const ni = Math.max(histIdx - 1, -1); setHistIdx(ni); setValue(ni === -1 ? '' : history[ni]); return }
  }

  const busy = jarvisState !== 'idle'

  return (
    <div className="glass scanline corner-tl corner-br relative p-3 flex flex-col gap-2">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-jarvis-cyan animate-pulse-slow" />
        <span className="font-mono text-[10px] text-jarvis-cyan/60 tracking-widest uppercase">
          Command Console
        </span>
        <div className="ml-auto flex gap-1">
          <span className={`font-mono text-[10px] px-2 py-0.5 rounded border ${busy ? 'text-yellow-400 border-yellow-400/40 bg-yellow-400/10' : 'text-green-400 border-green-400/40 bg-green-400/10'}`}>
            {busy ? jarvisState.toUpperCase() : 'READY'}
          </span>
        </div>
      </div>

      {/* Input row */}
      <div className="flex items-center gap-2">
        <span className="font-mono text-jarvis-cyan text-sm shrink-0">
          {busy ? '⟳' : '▶'}
        </span>
        <input
          ref={inputRef}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
          placeholder={busy ? 'Processing…' : 'Ask JARVIS…  (↑↓ history, Enter to submit)'}
          className="flex-1 bg-transparent border-none outline-none font-mono text-sm text-slate-200 placeholder-slate-600 caret-jarvis-cyan disabled:opacity-40"
        />
        <motion.button
          whileTap={{ scale: 0.93 }}
          onClick={submit}
          disabled={busy || !value.trim()}
          className="px-3 py-1 text-xs font-mono border border-jarvis-cyan/40 text-jarvis-cyan rounded hover:bg-jarvis-cyan/10 transition disabled:opacity-30"
        >
          SEND
        </motion.button>
      </div>

      {/* Bottom bar */}
      <div className="h-px bg-gradient-to-r from-transparent via-jarvis-cyan/30 to-transparent" />
      <p className="font-mono text-[9px] text-slate-700">
        ↑↓ HISTORY  ·  ENTER SUBMIT  ·  ESC ABORT
      </p>
    </div>
  )
}
