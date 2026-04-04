import React, { useEffect } from 'react';
import { View, StyleSheet } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
} from 'react-native-reanimated';
import { COLORS } from '../utils/colors';

export default function AnimatedOrb({ state }) {
  // state: 'idle' | 'reasoning'
  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.5);
  const rotation = useSharedValue(0);

  useEffect(() => {
    if (state === 'reasoning') {
      scale.value = withRepeat(withSequence(withTiming(1.15, { duration: 800 }), withTiming(1, { duration: 800 })), -1, true);
      opacity.value = withRepeat(withTiming(0.9, { duration: 800 }), -1, true);
    } else {
      scale.value = withTiming(1, { duration: 1000 });
      opacity.value = withRepeat(withSequence(withTiming(0.8, { duration: 2000 }), withTiming(0.4, { duration: 2000 })), -1, true);
    }
    
    rotation.value = withRepeat(
      withTiming(360, { duration: state === 'idle' ? 15000 : 5000, easing: Easing.linear }),
      -1,
      false
    );
  }, [state]);

  const coreStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  const ringStyle = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotation.value}deg` }],
  }));

  const c = state === 'reasoning' ? COLORS.purple : COLORS.cyan;

  return (
    <View style={styles.container}>
      {/* Outer Ring */}
      <Animated.View style={[styles.ring, { width: 140, height: 140, borderColor: c }, ringStyle]} />
      {/* Middle Ring (rotates opposite) */}
      <Animated.View style={[styles.ring, { width: 100, height: 100, borderColor: c }, { transform: [{ rotate: `-${rotation.value}deg` }] }]} />
      
      {/* Inner Core */}
      <Animated.View style={[styles.core, { backgroundColor: c, shadowColor: c }, coreStyle]} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: 160,
    height: 160,
    justifyContent: 'center',
    alignItems: 'center',
  },
  ring: {
    position: 'absolute',
    borderWidth: 1,
    borderRadius: 100,
    opacity: 0.3,
  },
  core: {
    width: 60,
    height: 60,
    borderRadius: 30,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 10,
  },
});
