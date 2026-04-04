import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

export default function AnimatedOrb({ state }) {
  // state: 'idle' | 'thinking' | 'executing' | 'speaking'
  const rings = [
    { r: 56,  delay: 0,    dur: 3 },
    { r: 76,  delay: 0.5,  dur: 4 },
    { r: 96,  delay: 1,    dur: 5 },
    { r: 116, delay: 1.5,  dur: 6 },
  ]

  const stateColors = {
    idle:      { core: '#00f2ff', ring: 'rgba(0,242,255,', shadow: '0 0 60px rgba(0,242,255,0.4)' },
    thinking:  { core: '#7c3aed', ring: 'rgba(124,58,237,', shadow: '0 0 80px rgba(124,58,237,0.6)' },
    executing: { core: '#ef4444', ring: 'rgba(239,68,68,',  shadow: '0 0 80px rgba(239,68,68,0.6)' },
    speaking:  { core: '#22c55e', ring: 'rgba(34,197,94,',  shadow: '0 0 80px rgba(34,197,94,0.6)' },
  }
  const c = stateColors[state] || stateColors.idle

  const stateLabel = {
    idle:      'STANDBY',
    thinking:  'REASONING',
    executing: 'EXECUTING',
    speaking:  'RESPONDING',
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 h-full">
      {/* Orb container */}
      <div className="relative flex items-center justify-center" style={{ width: 240, height: 240 }}>
        {/* Rotating rings */}
        {rings.map((ring, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: ring.r * 2,
              height: ring.r * 2,
              border: `1px solid ${c.ring}${state === 'idle' ? '0.2' : '0.35'})`,
              boxShadow: `0 0 8px ${c.ring}0.1)`,
            }}
            animate={{ rotate: i % 2 === 0 ? 360 : -360 }}
            transition={{ duration: ring.dur * (state === 'idle' ? 3 : 1.2), repeat: Infinity, ease: 'linear' }}
          />
        ))}

        {/* Core glow background */}
        <motion.div
          className="absolute rounded-full"
          style={{ width: 100, height: 100 }}
          animate={{
            scale: state === 'idle' ? [1, 1.06, 1] : [1, 1.2, 1],
            opacity: state === 'idle' ? [0.5, 0.8, 0.5] : [0.7, 1, 0.7],
          }}
          transition={{ duration: state === 'idle' ? 3 : 1.2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <div
            className="w-full h-full rounded-full"
            style={{
              background: `radial-gradient(circle, ${c.core}40 0%, ${c.core}10 60%, transparent 100%)`,
              boxShadow: c.shadow,
            }}
          />
        </motion.div>

        {/* Core sphere */}
        <motion.div
          className="relative z-10 rounded-full flex items-center justify-center"
          style={{
            width: 72, height: 72,
            background: `radial-gradient(circle at 35% 35%, ${c.core}80, ${c.core}20 60%, transparent)`,
            boxShadow: `${c.shadow}, inset 0 0 20px ${c.ring}0.3)`,
            border: `1px solid ${c.ring}0.6)`,
          }}
          animate={{ scale: state === 'thinking' ? [1, 1.08, 1] : 1 }}
          transition={{ duration: 0.8, repeat: state === 'thinking' ? Infinity : 0 }}
        >
          {/* JARVIS hex symbol */}
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <polygon
              points="16,2 28,9 28,23 16,30 4,23 4,9"
              stroke={c.core}
              strokeWidth="1.5"
              fill="none"
              opacity="0.9"
            />
            <polygon
              points="16,8 23,12 23,20 16,24 9,20 9,12"
              fill={c.core}
              opacity="0.15"
            />
            <circle cx="16" cy="16" r="3" fill={c.core} opacity="0.9" />
          </svg>
        </motion.div>

        {/* Ticker dots around ring */}
        {[0,60,120,180,240,300].map((angle, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full"
            style={{
              width: 4, height: 4,
              background: c.core,
              top: '50%', left: '50%',
              marginTop: -2, marginLeft: -2,
              transformOrigin: '2px 2px',
              transform: `rotate(${angle}deg) translateY(-116px)`,
              opacity: 0.5,
            }}
            animate={{ opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 2, delay: i * 0.3, repeat: Infinity }}
          />
        ))}
      </div>

      {/* State label */}
      <div className="text-center">
        <motion.p
          key={state}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-hud text-sm tracking-[0.3em] uppercase glow-text"
          style={{ color: c.core }}
        >
          {stateLabel[state]}
        </motion.p>
        <p className="font-mono text-xs text-slate-600 mt-1">J.A.R.V.I.S. CORE v16</p>
      </div>
    </div>
  )
}
