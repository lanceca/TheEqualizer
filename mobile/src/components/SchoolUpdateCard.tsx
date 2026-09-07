import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import { truncateWords } from "../lib/api";
import type { SchoolUpdate } from "../lib/types";
import { colors, typography } from "../theme";

export function SchoolUpdateCard({
  update,
  compact = false,
}: {
  update: SchoolUpdate;
  compact?: boolean;
}) {
  const open = () => {
    router.push({
      pathname: "/school-updates/[slug]",
      params: { slug: update.slug },
    });
  };

  return (
    <Pressable style={styles.card} onPress={open}>
      <Text style={styles.label}>School Update</Text>

      {update.image_url ? (
        <Image
          source={{ uri: update.image_url }}
          style={styles.image}
          resizeMode="cover"
        />
      ) : (
        <View style={[styles.image, styles.placeholder]} />
      )}

      <View style={styles.copy}>
        <Text style={styles.title}>{update.title}</Text>
        <Text style={styles.summary} numberOfLines={compact ? 3 : undefined}>
          {compact ? truncateWords(update.summary, 24) : update.summary}
        </Text>
        <Text style={styles.readMore}>View full details</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.white,
  },
  label: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: colors.green,
    color: colors.white,
    fontSize: 10,
    fontWeight: "800",
    letterSpacing: 1.1,
    textTransform: "uppercase",
  },
  image: {
    width: "100%",
    aspectRatio: 16 / 9,
    backgroundColor: colors.soft,
  },
  placeholder: {
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  copy: {
    paddingHorizontal: 16,
    paddingTop: 15,
    paddingBottom: 17,
  },
  title: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 21,
    lineHeight: 26,
    fontWeight: "700",
  },
  summary: {
    marginTop: 8,
    color: colors.muted,
    fontSize: 13,
    lineHeight: 20,
  },
  readMore: {
    marginTop: 11,
    color: colors.green,
    fontSize: 12,
    fontWeight: "800",
  },
});
