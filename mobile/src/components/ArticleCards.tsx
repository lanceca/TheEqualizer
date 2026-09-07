import { Image, Pressable, StyleSheet, Text, View } from "react-native";
import { router } from "expo-router";

import {
  formatDate,
  truncateWords,
} from "../lib/api";
import type { ArticleSummary } from "../lib/types";
import { colors, typography } from "../theme";

function openArticle(slug: string) {
  router.push({
    pathname: "/article/[slug]",
    params: { slug },
  });
}

function StoryImage({
  article,
  style,
}: {
  article: ArticleSummary;
  style: object;
}) {
  if (article.hero_image_url) {
    return (
      <Image
        source={{ uri: article.hero_image_url }}
        style={style}
        resizeMode="cover"
      />
    );
  }

  return (
    <View style={[style, styles.placeholder]}>
      <Text style={styles.placeholderText}>The Equalizer</Text>
    </View>
  );
}

export function LeadStory({ article }: { article: ArticleSummary }) {
  const deck = article.subtitle || article.excerpt;

  return (
    <View style={styles.leadStory}>
      <Pressable onPress={() => openArticle(article.slug)}>
        <StoryImage article={article} style={styles.leadImage} />
      </Pressable>

      <View style={styles.leadContent}>
        <Text style={styles.category}>{article.category.name}</Text>

        <Pressable onPress={() => openArticle(article.slug)}>
          <Text style={styles.leadTitle}>{article.title}</Text>
        </Pressable>

        {deck ? (
          <Text style={styles.deck}>
            {truncateWords(deck, 32)}
          </Text>
        ) : null}

        <Text style={styles.meta}>
          By <Text style={styles.metaStrong}>{article.author.display_name}</Text>
          {article.published_at
            ? `  ·  ${formatDate(article.published_at)}`
            : ""}
        </Text>

        {article.excerpt ? (
          <Text style={styles.excerpt}>
            {truncateWords(article.excerpt, 48)}
          </Text>
        ) : null}

        <Pressable onPress={() => openArticle(article.slug)}>
          <Text style={styles.readLink}>Read full story</Text>
        </Pressable>
      </View>
    </View>
  );
}

export function SecondaryStory({ article }: { article: ArticleSummary }) {
  return (
    <Pressable
      style={styles.secondaryStory}
      onPress={() => openArticle(article.slug)}
    >
      <StoryImage article={article} style={styles.secondaryImage} />

      <View style={styles.secondaryContent}>
        <Text style={styles.category}>{article.category.name}</Text>
        <Text style={styles.secondaryTitle} numberOfLines={3}>
          {article.title}
        </Text>
        <Text style={styles.meta} numberOfLines={2}>
          By {article.author.display_name}
          {article.published_at
            ? `  ·  ${formatDate(article.published_at)}`
            : ""}
        </Text>
      </View>
    </Pressable>
  );
}

export function StoryCard({ article }: { article: ArticleSummary }) {
  return (
    <View style={styles.storyCard}>
      <Pressable onPress={() => openArticle(article.slug)}>
        <StoryImage article={article} style={styles.storyCardImage} />
      </Pressable>

      <View style={styles.storyCardBody}>
        <Text style={styles.category}>{article.category.name}</Text>

        <Pressable onPress={() => openArticle(article.slug)}>
          <Text style={styles.storyCardTitle}>{article.title}</Text>
        </Pressable>

        <Text style={styles.meta}>
          By {article.author.display_name}
          {article.published_at
            ? `  ·  ${formatDate(article.published_at)}`
            : ""}
        </Text>

        {article.excerpt ? (
          <Text style={styles.storyCardExcerpt}>
            {truncateWords(article.excerpt, 28)}
          </Text>
        ) : null}
      </View>
    </View>
  );
}

export function CategoryFeaturedStory({
  article,
}: {
  article: ArticleSummary;
}) {
  return (
    <View style={styles.categoryFeatured}>
      <Pressable onPress={() => openArticle(article.slug)}>
        <StoryImage article={article} style={styles.categoryFeaturedImage} />
      </Pressable>

      <View style={styles.categoryFeaturedCopy}>
        <Text style={styles.category}>{article.category.name}</Text>

        <Pressable onPress={() => openArticle(article.slug)}>
          <Text style={styles.categoryFeaturedTitle}>
            {article.title}
          </Text>
        </Pressable>

        {article.subtitle || article.excerpt ? (
          <Text style={styles.deck}>
            {truncateWords(article.subtitle || article.excerpt, 32)}
          </Text>
        ) : null}

        <Text style={styles.meta}>
          By <Text style={styles.metaStrong}>{article.author.display_name}</Text>
          {article.published_at
            ? `  ·  ${formatDate(article.published_at)}`
            : ""}
        </Text>

        {article.excerpt ? (
          <Text style={styles.excerpt}>
            {truncateWords(article.excerpt, 52)}
          </Text>
        ) : null}

        <Pressable onPress={() => openArticle(article.slug)}>
          <Text style={styles.readLink}>Read full story</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  placeholder: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#e6eee9",
  },
  placeholderText: {
    color: colors.green,
    fontFamily: typography.serif,
    fontSize: 22,
    fontWeight: "700",
  },
  category: {
    marginBottom: 7,
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.05,
    textTransform: "uppercase",
  },
  meta: {
    marginTop: 12,
    color: colors.muted,
    fontSize: 12,
    lineHeight: 18,
  },
  metaStrong: {
    fontWeight: "800",
  },
  deck: {
    marginTop: 13,
    color: "#3e4944",
    fontFamily: typography.serif,
    fontSize: 18,
    lineHeight: 26,
  },
  excerpt: {
    marginTop: 14,
    color: "#3f4a45",
    fontSize: 14.5,
    lineHeight: 23,
  },
  readLink: {
    marginTop: 16,
    color: colors.green,
    fontSize: 14,
    fontWeight: "800",
  },
  leadStory: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.white,
  },
  leadImage: {
    width: "100%",
    aspectRatio: 16 / 9,
    backgroundColor: colors.soft,
  },
  leadContent: {
    padding: 20,
  },
  leadTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 34,
    lineHeight: 37,
    fontWeight: "700",
  },
  secondaryStory: {
    flexDirection: "row",
    gap: 13,
    paddingBottom: 15,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  secondaryImage: {
    width: 118,
    height: 88,
    borderRadius: 8,
    backgroundColor: colors.soft,
  },
  secondaryContent: {
    flex: 1,
    minWidth: 0,
  },
  secondaryTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 20,
    lineHeight: 23,
    fontWeight: "700",
  },
  storyCard: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    backgroundColor: colors.white,
  },
  storyCardImage: {
    width: "100%",
    aspectRatio: 16 / 10,
    backgroundColor: colors.soft,
  },
  storyCardBody: {
    paddingHorizontal: 17,
    paddingTop: 16,
    paddingBottom: 19,
  },
  storyCardTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 24,
    lineHeight: 28,
    fontWeight: "700",
  },
  storyCardExcerpt: {
    marginTop: 12,
    color: "#3f4a45",
    fontSize: 13.5,
    lineHeight: 21,
  },
  categoryFeatured: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    backgroundColor: colors.white,
  },
  categoryFeaturedImage: {
    width: "100%",
    aspectRatio: 16 / 9,
    backgroundColor: colors.soft,
  },
  categoryFeaturedCopy: {
    paddingHorizontal: 20,
    paddingTop: 22,
    paddingBottom: 25,
  },
  categoryFeaturedTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 32,
    lineHeight: 36,
    fontWeight: "700",
  },
});
