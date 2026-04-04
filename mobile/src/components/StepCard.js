import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { COLORS } from '../utils/colors';

const TOOL_COLORS = {
  web_search: COLORS.blue,
  code_runner: COLORS.green,
  file_manager: COLORS.yellow,
  system_control: COLORS.red,
  default: COLORS.cyan,
};

export default function StepCard({ step }) {
  if (step.type === 'user') {
    return (
      <View style={[styles.card, { borderLeftColor: COLORS.purple }]}>
        <Text style={styles.header}>👤 USER</Text>
        <Text style={styles.body}>{step.text}</Text>
      </View>
    );
  }

  if (step.type === 'answer') {
    return (
      <View style={[styles.card, { borderLeftColor: COLORS.cyan, backgroundColor: 'rgba(0,242,255,0.05)' }]}>
        <Text style={[styles.header, { color: COLORS.cyan }]}>🧠 JARVIS</Text>
        <Text style={styles.body}>{step.text}</Text>
      </View>
    );
  }

  const c = TOOL_COLORS[step.tool] || TOOL_COLORS.default;

  return (
    <View style={[styles.card, { borderLeftColor: c }]}>
      <Text style={[styles.header, { color: c }]}>⚙️ ACTION: {step.tool}</Text>
      
      {!!step.input && (
        <View style={styles.block}>
          <Text style={styles.subHeader}>📥 INPUT</Text>
          <Text style={styles.code}>{step.input.trim().slice(0, 200)}</Text>
        </View>
      )}

      {!!step.obs && (
        <View style={styles.block}>
          <Text style={styles.subHeader}>📡 OBSERVATION</Text>
          <Text style={styles.code}>{step.obs.trim().slice(0, 200)}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.panel,
    borderRadius: 8,
    borderLeftWidth: 3,
    padding: 12,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  header: {
    color: COLORS.textMuted,
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 4,
    fontFamily: 'Courier',
  },
  body: {
    color: COLORS.text,
    fontSize: 14,
  },
  block: {
    marginTop: 8,
  },
  subHeader: {
    color: COLORS.textMuted,
    fontSize: 10,
    marginBottom: 2,
    fontFamily: 'Courier',
  },
  code: {
    color: '#cbd5e1',
    fontFamily: 'Courier',
    fontSize: 12,
    backgroundColor: 'rgba(0,0,0,0.4)',
    padding: 6,
    borderRadius: 4,
  },
});
