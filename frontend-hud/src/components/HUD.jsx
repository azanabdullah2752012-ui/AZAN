import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import TopBar          from './TopBar'
import AnimatedOrb     from './AnimatedOrb'
import CommandConsole  from './CommandConsole'
import TelemetryPanel  from './TelemetryPanel'
import ConversationPanel from './ConversationPanel'

export default function HUD({ status, model, setModel, steps, jarvisState, memory, uptime, onCommand }) {
  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-jarvis-bg"
         style={{ background: 'radial-gradient(ellipse at 50% 0%, #0d1f3a 0%, #030712 70%)' }}>

      {/* Background grid */}
      <div className="fixed inset-0 pointer-events-none opacity-20"
           style={{
             backgroundImage: `linear-gradient(rgba(0,242,255,0.08) 1px, transparent 1px),
                               linear-gradient(90deg, rgba(0,242,255,0.08) 1px, transparent 1px)`,
             backgroundSize: '80px 80px'
           }} />

      {/* Top Bar */}
      <TopBar status={status} model={model} setModel={setModel} uptime={uptime} />

      {/* Center 3-column layout */}
      <div className="flex-1 flex gap-2 p-4 overflow-hidden min-h-0 relative">
        
        {/* LEFT — Conversation Reasoning Stream */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex flex-col z-10"
          style={{ width: '30%' }}
        >
          <div className="glass p-1 h-full overflow-hidden flex flex-col">
            <ConversationPanel steps={steps} jarvisState={jarvisState} />
          </div>
        </motion.div>

        {/* CENTER — Cinematic Mic + Orb */}
        <div className="flex-1 flex flex-col items-center justify-center relative z-0">
          <div className="relative group cursor-pointer" onClick={() => onCommand("listen")}>
             {/* Circular Mic Button (Iron Man Style) */}
             <div className="absolute inset-0 bg-cyan-500/20 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity rounded-full" />
             <div className="w-48 h-48 rounded-full glass border-2 border-cyan-500/30 flex items-center justify-center relative overflow-hidden animate-pulse-cyan">
                <AnimatedOrb state={jarvisState} />
                {/* Waveform Animation */}
                {status === 'listening' && (
                  <div className="absolute bottom-4 flex items-end h-10">
                    <div className="wave-bar" style={{ animationDelay: '0.1s' }} />
                    <div className="wave-bar" style={{ animationDelay: '0.3s' }} />
                    <div className="wave-bar" style={{ animationDelay: '0.2s' }} />
                    <div className="wave-bar" style={{ animationDelay: '0.5s' }} />
                    <div className="wave-bar" style={{ animationDelay: '0.1s' }} />
                  </div>
                )}
             </div>
             {/* Action Badge */}
             <AnimatePresence>
               {jarvisState && jarvisState !== 'idle' && (
                 <motion.div 
                   initial={{ opacity: 0, y: 20 }}
                   animate={{ opacity: 1, y: 0 }}
                   exit={{ opacity: 0, y: -20 }}
                   className="absolute -bottom-10 left-1/2 -translate-x-1/2 glass px-4 py-1 flex items-center gap-2 border-cyan-500/50"
                 >
                   <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />
                   <span className="text-cyan-400 font-hud text-xs uppercase tracking-widest">
                     {jarvisState === 'thinking' ? '⚙️ Processing' : '🔊 Speaking'}
                   </span>
                 </motion.div>
               )}
             </AnimatePresence>
          </div>
          
          <div className="mt-20 w-full max-w-xl">
            <CommandConsole onCommand={onCommand} jarvisState={jarvisState} />
          </div>
        </div>

        {/* RIGHT — Telemetry */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex flex-col gap-2 z-10"
          style={{ width: '25%' }}
        >
          <TelemetryPanel status={status} />
          
          <div className="glass p-4">
             <div className="font-hud text-[10px] tracking-[0.3em] uppercase text-cyan-400/60 mb-3">Active System Overlays</div>
             <div className="space-y-2">
                <div className="telemetry-item flex justify-between">
                   <span>OS LAYER:</span>
                   <span className="text-cyan-400">DARWIN/ARM64</span>
                </div>
                <div className="telemetry-item flex justify-between">
                   <span>SECURE LINK:</span>
                   <span className="text-green-500">ENCRYPTED</span>
                </div>
                <div className="telemetry-item flex justify-between">
                   <span>AUTOMATION:</span>
                   <span className="text-cyan-400">NOMINAL</span>
                </div>
             </div>
          </div>
        </motion.div>

      </div>

      {/* Bottom status bar */}
      <div className="glass shrink-0 flex items-center justify-between px-6 py-2 border-t border-cyan-500/20"
           style={{ borderRadius: 0 }}>
        <div className="flex items-center gap-4">
           <span className="font-hud text-[10px] text-cyan-400/50 uppercase tracking-[0.5em]">
             JARVIS MK-II // SYSTEM OVERRIDE ACTIVE
           </span>
        </div>
        <div className="flex gap-6">
           <span className="telemetry-item">UPTIME: {uptime}</span>
           <span className="telemetry-item">TEMP: 42°C</span>
           <span className="telemetry-item text-green-500">STABLE</span>
        </div>
      </div>
    </div>
  )
}
