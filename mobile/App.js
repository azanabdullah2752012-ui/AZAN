import React, { useState, useEffect, useRef } from 'react';
import { View, Text, TextInput, StyleSheet, ScrollView, TouchableOpacity, SafeAreaView, KeyboardAvoidingView, Platform } from 'react-native';
import { COLORS } from './src/utils/colors';
import AnimatedOrb from './src/components/AnimatedOrb';
import StepCard from './src/components/StepCard';
import SocketManager from './src/services/SocketManager';

// Set this to your Mac's Local IP Address
const MAC_IP = '192.168.0.8'; 
const DEVICE_TOKEN = 'JARVIS-MOBILE-001';

export default function App() {
  const [status, setStatus] = useState('disconnected');
  const [orbState, setOrbState] = useState('idle'); // 'idle' | 'reasoning' | 'listening'
  const [steps, setSteps] = useState([]);
  const [input, setInput] = useState('');
  const scrollViewRef = useRef(null);
  const sm = useRef(null);
  
  // Track the current executing step to append chunks to it
  const currentStep = useRef(null);

  useEffect(() => {
    sm.current = new SocketManager(MAC_IP, DEVICE_TOKEN, setStatus, handleMessage);
    sm.current.connect();
    return () => sm.current.disconnect();
  }, []);

  const handleMessage = (msg) => {
    if (msg.type === 'system') {
      console.log('System:', msg.message);
    } 
    else if (msg.type === 'state_stream' && msg.data) {
      if (msg.data.answer) {
        setOrbState('idle');
        setSteps(prev => [...prev, { type: 'answer', text: msg.data.answer }]);
        currentStep.current = null;
      }
    }
    else if (msg.type === 'step_stream' && msg.data) {
      setOrbState('reasoning');
      if (msg.data.type === 'start') {
        currentStep.current = { id: msg.data.id, type: msg.data.step_type, text: msg.data.text, status: 'in_progress' };
        setSteps(prev => [...prev, currentStep.current]);
      } else if (msg.data.type === 'chunk' && currentStep.current && currentStep.current.id === msg.data.id) {
        setSteps(prev => prev.map(step =>
          step.id === msg.data.id ? { ...step, text: step.text + msg.data.text } : step
        ));
      } else if (msg.data.type === 'end' && currentStep.current && currentStep.current.id === msg.data.id) {
        setSteps(prev => prev.map(step =>
          step.id === msg.data.id ? { ...step, status: 'completed' } : step
        ));
      }
    }
    else if (msg.type === 'ack') {
      setOrbState('reasoning');
    }
  };

  const sendCommand = () => {
    if (!input.trim()) return;
    setSteps(prev => [...prev, { type: 'user', text: input }]);
    sm.current.sendCommand(input);
    setInput('');
  };

  const toggleVoice = () => {
    if (orbState === 'listening') {
      setOrbState('idle');
    } else {
      setOrbState('listening');
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        
        {/* Header - Glassmorphism style */}
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>AZAN MOBILE</Text>
            <Text style={styles.subtitle}>AUTONOMOUS SYSTEM v1.0</Text>
          </View>
          <View style={styles.statusRow}>
            <View style={[styles.dot, { backgroundColor: status === 'connected' ? COLORS.green : COLORS.red, shadowColor: status === 'connected' ? COLORS.green : COLORS.red, shadowOpacity: 1, shadowRadius: 10 }]} />
            <Text style={styles.statusText}>{status.toUpperCase()}</Text>
          </View>
        </View>

        {/* Central Orb / HUD Area */}
        <View style={styles.orbContainer}>
          <View style={styles.hudRing}>
            <AnimatedOrb state={orbState} />
          </View>
          <View style={styles.orbStatusBox}>
            <Text style={styles.orbLabel}>
              {orbState === 'idle' ? 'STANDBY' : orbState === 'listening' ? 'LISTENING' : 'PROCESSING'}
            </Text>
            {orbState !== 'idle' && <Text style={styles.pulseText}>SYSTEM ACTIVE</Text>}
          </View>
        </View>

        {/* Communication Stream */}
        <ScrollView 
          style={styles.stream} 
          contentContainerStyle={styles.streamContent}
          ref={scrollViewRef}
          onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        >
          {steps.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>INITIATE COMMAND OR VOICE OVERRIDE</Text>
            </View>
          ) : (
            steps.map((s, i) => <StepCard key={i} step={s} />)
          )}
        </ScrollView>

        {/* Console / Voice Control */}
        <View style={styles.inputConsole}>
          <TouchableOpacity 
            style={[styles.voiceBtn, orbState === 'listening' && styles.voiceBtnActive]} 
            onPress={toggleVoice}
          >
            <Text style={[styles.voiceIcon, orbState === 'listening' && { color: '#fff' }]}>◎</Text>
          </TouchableOpacity>
          
          <View style={styles.inputWrapper}>
            <TextInput
              style={styles.input}
              placeholder="Enter digital command..."
              placeholderTextColor="rgba(0,242,255,0.3)"
              value={input}
              onChangeText={setInput}
              onSubmitEditing={sendCommand}
            />
          </View>

          <TouchableOpacity 
            style={[styles.sendBtn, { opacity: input.trim() ? 1 : 0.4 }]} 
            onPress={sendCommand}
            disabled={!input.trim()}
          >
            <Text style={styles.sendText}>▲</Text>
          </TouchableOpacity>
        </View>

      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: COLORS.bg },
  container: { flex: 1 },
  header: { 
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', 
    paddingHorizontal: 25, paddingVertical: 15,
    borderBottomWidth: 1, borderBottomColor: COLORS.border,
    backgroundColor: 'rgba(6,15,30,0.5)'
  },
  title: { color: COLORS.cyan, fontWeight: '900', letterSpacing: 3, fontSize: 18, textShadowColor: COLORS.cyan, textShadowOffset: {width: 0, height: 0}, textShadowRadius: 10 },
  subtitle: { color: COLORS.textMuted, fontSize: 8, letterSpacing: 2, marginTop: 2 },
  statusRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.05)', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 15 },
  dot: { width: 6, height: 6, borderRadius: 3, marginRight: 8 },
  statusText: { color: COLORS.text, fontSize: 10, letterSpacing: 1, fontWeight: '600' },
  
  orbContainer: { 
    height: 260, justifyContent: 'center', alignItems: 'center',
    borderBottomWidth: 1, borderBottomColor: COLORS.border,
    backgroundColor: 'rgba(0,0,0,0.2)'
  },
  hudRing: {
    width: 180, height: 180, borderRadius: 90, borderWidth: 1, borderColor: 'rgba(0,242,255,0.1)',
    justifyContent: 'center', alignItems: 'center',
    shadowColor: COLORS.cyan, shadowOpacity: 0.1, shadowRadius: 20
  },
  orbStatusBox: { position: 'absolute', bottom: 20, alignItems: 'center' },
  orbLabel: {
    color: COLORS.cyan, fontSize: 10, letterSpacing: 5, fontWeight: 'bold'
  },
  pulseText: { color: COLORS.textMuted, fontSize: 8, letterSpacing: 2, marginTop: 5, opacity: 0.6 },
  
  stream: { flex: 1 },
  streamContent: { padding: 20, paddingBottom: 40 },
  emptyState: { flex: 1, height: 100, justifyContent: 'center', alignItems: 'center', opacity: 0.3 },
  emptyText: { color: COLORS.cyan, fontSize: 10, letterSpacing: 3, textAlign: 'center' },

  inputConsole: {
    flexDirection: 'row', paddingHorizontal: 20, paddingVertical: 15,
    borderTopWidth: 1, borderTopColor: COLORS.border,
    backgroundColor: '#030712', alignItems: 'center'
  },
  voiceBtn: {
    width: 45, height: 45, borderRadius: 22.5, backgroundColor: 'rgba(0,242,255,0.05)',
    borderWidth: 1, borderColor: COLORS.border, justifyContent: 'center', alignItems: 'center'
  },
  voiceBtnActive: { backgroundColor: COLORS.cyan, borderColor: COLORS.cyan },
  voiceIcon: { color: COLORS.cyan, fontSize: 24 },
  
  inputWrapper: { flex: 1, marginHorizontal: 12 },
  input: {
    backgroundColor: 'rgba(255,255,255,0.03)',
    color: COLORS.text, borderRadius: 25, paddingHorizontal: 20, paddingVertical: 10,
    borderWidth: 1, borderColor: 'rgba(0,242,255,0.1)', fontSize: 14
  },
  sendBtn: {
    width: 45, height: 45, borderRadius: 22.5, backgroundColor: 'rgba(0,242,255,0.1)',
    justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: COLORS.cyan
  },
  sendText: { color: COLORS.cyan, fontSize: 18 }
});
