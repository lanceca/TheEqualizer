import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import { formatDate } from "../lib/api";
import type { ArticleSummary } from "../lib/types";
import { colors } from "../theme/colors";

type Props = {
  article: ArticleSummary;
  compact?: boolean;
};

export function ArticleCard({ article, compact = false }: Props) {
  const openArticle = () => {
    router.push({
      pathname: "/article/[slug]",
      params: { slug: article.slug },
    });
  };

  return (
    <Pressable
      onPress={openArticle}
      style={({ pressed }) => [
        styles.card,
        compact && styles.compactCard,
        pressed && styles.pressed,
      ]}
    >
      <View style={[styles.media, compact && styles.compactMedia]}>
        {article.hero_image_url ? (
          <Image
            source={{ uri: article.hero_image_url }}
            style={[styles.image, compact && styles.compactImage]}
            resizeMode="cover"
          />
        ) : (
          <View
            style={[
              styles.image,
              styles.placeholder,
              compact && styles.compactImage,
            ]}
          >
            <Text style={styles.placeholderText}>THE EQUALIZER</Text>
          </View>
        )}

        {article.is_archived ? (
          <View style={styles.archiveBadge}>
            <Text style={styles.archiveBadgeText}>ARCHIVED</Text>
          </View>
        ) : null}
      </View>

      <View style={styles.content}>
        <Text style={styles.category}>{article.category.name}</Text>
        <Text
          style={[styles.title, compact && styles.compactTitle]}
          numberOfLines={compact ? 2 : 3}
        >
          {article.title}
        </Text>

        {!compact && article.excerpt ? (
          <Text style={styles.excerpt} numberOfLines={3}>
            {article.excerpt}
          </Text>
        ) : null}

        <View style={styles.metaRow}>
          <Text style={styles.meta} numberOfLines={1}>
            {article.author.display_name}
          </Text>
          <Text style={styles.dot}>•</Text>
          <Text style={styles.meta}>{formatDate(article.published_at)}</Text>
        </View>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    overflow: "hidden",
    borderRadius: 16,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
  },
  compactCard: { flexDirection: "row" },
  pressed: { opacity: 0.82 },
  media: { position: "relative" },
  compactMedia: { width: 118 },
  image: {
    width: "100%",
    height: 190,
    backgroundColor: colors.softGreen,
  },
  compactImage: { width: 118, height: 118 },
  placeholder: { alignItems: "center", justifyContent: "center" },
  placeholderText: {
    color: colors.forest,
    fontWeight: "900",
    fontSize: 12,
    letterSpacing: 1,
  },
  archiveBadge: {
    position: "absolute",
    top: 10,
    left: 10,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: "rgba(14, 42, 34, 0.90)",
  },
  archiveBadgeText: {
    color: "#FFFFFF",
    fontSize: 9.5,
    fontWeight: "900",
    letterSpacing: 0.9,
  },
  content: { flex: 1, padding: 15, gap: 7 },
  category: {
    color: colors.gold,
    fontWeight: "800",
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.7,
  },
  title: {
    color: colors.forestDark,
    fontWeight: "800",
    fontSize: 20,
    lineHeight: 25,
  },
  compactTitle: { fontSize: 16, lineHeight: 20 },
  excerpt: { color: colors.muted, fontSize: 14, lineHeight: 20 },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: 6,
  },
  meta: { color: colors.muted, fontSize: 12 },
  dot: { color: colors.gold },
});
