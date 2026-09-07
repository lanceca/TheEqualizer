import { ActivityIndicator, Pressable, StyleSheet, Text, View } from "react-native";

import { colors } from "../theme";

type Props = {
  loading?: boolean;
  message?: string;
  onRetry?: () => void;
};

export function ScreenState({ loading = false, message, onRetry }: Props) {
  return (
    <View style={styles.container}>
      {loading ? <ActivityIndicator size="large" color={colors.green} /> : null}
      {message ? <Text style={styles.message}>{message}</Text> : null}

      {onRetry ? (
        <Pressable style={styles.button} onPress={onRetry}>
          <Text style={styles.buttonText}>Try again</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    minHeight: 260,
    paddingHorizontal: 24,
    alignItems: "center",
    justifyContent: "center",
    gap: 14,
    backgroundColor: colors.white,
  },
  message: {
    color: colors.muted,
    textAlign: "center",
    lineHeight: 21,
    fontSize: 14,
  },
  button: {
    borderRadius: 999,
    backgroundColor: colors.green,
    paddingHorizontal: 18,
    paddingVertical: 11,
  },
  buttonText: {
    color: colors.white,
    fontWeight: "800",
  },
});
