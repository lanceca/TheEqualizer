import type { ReactNode } from "react";
import { createContext, useContext, useEffect, useMemo, useRef } from "react";
import { Animated, StyleSheet, type StyleProp, type ViewStyle } from "react-native";

const SkeletonAnimationContext = createContext<Animated.Value | null>(null);

export function SkeletonProvider({ children }: { children: ReactNode }) {
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(Animated.sequence([
      Animated.timing(progress, { toValue: 1, duration: 820, useNativeDriver: true }),
      Animated.timing(progress, { toValue: 0, duration: 820, useNativeDriver: true }),
    ]));
    loop.start();
    return () => loop.stop();
  }, [progress]);
  return <SkeletonAnimationContext.Provider value={progress}>{children}</SkeletonAnimationContext.Provider>;
}

export function SkeletonBlock({ style }: { style?: StyleProp<ViewStyle> }) {
  const progress = useContext(SkeletonAnimationContext);
  const opacity = useMemo(() => progress ? progress.interpolate({ inputRange: [0, 1], outputRange: [0.5, 1] }) : 0.72, [progress]);
  return <Animated.View accessible={false} importantForAccessibility="no" style={[styles.block, style, { opacity }]} />;
}

const styles = StyleSheet.create({ block: { backgroundColor: "#DDE6E1", borderRadius: 8 } });
