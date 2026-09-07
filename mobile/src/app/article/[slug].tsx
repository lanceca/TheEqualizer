import { useCallback, useEffect, useState } from "react";
import {
  Image,
  Linking,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams } from "expo-router";

import { ScreenState } from "../../components/ScreenState";
import { SiteHeader } from "../../components/SiteHeader";
import {
  SITE_ORIGIN,
  apiGet,
  apiPost,
  formatDate,
  stripHtml,
} from "../../lib/api";
import type {
  ArticleDetailResponse,
  ArticleEngagementActionResponse,
} from "../../lib/types";
import { colors, typography } from "../../theme";

export default function ArticleScreen() {
  const params = useLocalSearchParams<{ slug: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;

  const [data, setData] = useState<ArticleDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reacting, setReacting] = useState(false);
  const [sharing, setSharing] = useState(false);

  const load = useCallback(async () => {
    if (!slug) return;

    setLoading(true);
    setError("");

    try {
      setData(
        await apiGet<ArticleDetailResponse>(
          `/articles/${encodeURIComponent(slug)}/`
        )
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load article."
      );
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const article = data?.article;

  const reactArticle = async () => {
    if (!article || reacting || data?.has_reacted) return;

    setReacting(true);

    try {
      const response = await apiPost<ArticleEngagementActionResponse>(
        `/articles/${encodeURIComponent(article.slug)}/react/`
      );

      setData((current) =>
        current
          ? {
              ...current,
              has_reacted: response.has_reacted ?? true,
              article: {
                ...current.article,
                engagement: response.engagement,
              },
            }
          : current
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to record reaction."
      );
    } finally {
      setReacting(false);
    }
  };

  const shareArticle = async () => {
    if (!article || sharing) return;

    setSharing(true);

    try {
      const result = await Share.share({
        message: `${article.title}\n${SITE_ORIGIN}/articles/${article.slug}/`,
      });

      if (result.action === Share.sharedAction) {
        const response = await apiPost<ArticleEngagementActionResponse>(
          `/articles/${encodeURIComponent(article.slug)}/share/`
        );

        setData((current) =>
          current
            ? {
                ...current,
                has_shared: response.has_shared ?? true,
                article: {
                  ...current.article,
                  engagement: response.engagement,
                },
              }
            : current
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to share this article."
      );
    } finally {
      setSharing(false);
    }
  };

  const downloadPdf = () => {
    if (!article) return;
    Linking.openURL(
      `${SITE_ORIGIN}/articles/${article.slug}/download-pdf/`
    );
  };

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !article ? (
        <ScreenState loading message="Loading article…" />
      ) : error && !article ? (
        <ScreenState message={error} onRetry={load} />
      ) : !article ? (
        <ScreenState message="Article not found." />
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
        >
          <View style={styles.header}>
            <Text style={styles.category}>{article.category.name}</Text>
            <Text style={styles.title}>{article.title}</Text>

            {article.subtitle ? (
              <Text style={styles.subtitle}>{article.subtitle}</Text>
            ) : null}

            <View style={styles.byline}>
              <View style={styles.bylineCopy}>
                <Text style={styles.bylineText}>
                  By{" "}
                  <Text style={styles.bylineStrong}>
                    {article.author.display_name}
                  </Text>
                </Text>

                {article.contributors.length > 0 ? (
                  <View style={styles.contributorList}>
                    {article.contributors.map((contributor, index) => (
                      <Text
                        key={`${contributor.username}-${contributor.role}-${index}`}
                        style={styles.contributor}
                      >
                        {contributor.display_name} — {contributor.role_display}
                      </Text>
                    ))}
                  </View>
                ) : null}
              </View>

              <Text style={styles.date}>
                {formatDate(article.published_at)}
              </Text>
            </View>
          </View>

          {article.featured_image_url ? (
            <View style={styles.featuredFigure}>
              <Image
                source={{ uri: article.featured_image_url }}
                style={styles.featuredImage}
                resizeMode="contain"
              />

              {article.featured_image_caption ||
              article.featured_image_credit ? (
                <View style={styles.captionRow}>
                  <Text style={styles.caption}>
                    {article.featured_image_caption}
                  </Text>
                  <Text style={styles.credit}>
                    {article.featured_image_credit}
                  </Text>
                </View>
              ) : null}
            </View>
          ) : null}

          {article.excerpt ? (
            <Text style={styles.standfirst}>{article.excerpt}</Text>
          ) : null}

          <Text style={styles.body}>{stripHtml(article.content)}</Text>

          {article.image_attachments.length > 0 ? (
            <View style={styles.mediaSection}>
              <Text style={styles.mediaKicker}>Article Media</Text>
              <Text style={styles.mediaHeading}>Images</Text>

              <View style={styles.gallery}>
                {article.image_attachments.map((attachment) => (
                  <View key={attachment.id} style={styles.galleryItem}>
                    <Image
                      source={{ uri: attachment.image_url }}
                      style={styles.galleryImage}
                      resizeMode="cover"
                    />

                    {attachment.caption || attachment.credit ? (
                      <View style={styles.captionRow}>
                        <Text style={styles.caption}>
                          {attachment.caption}
                        </Text>
                        <Text style={styles.credit}>
                          {attachment.credit}
                        </Text>
                      </View>
                    ) : null}
                  </View>
                ))}
              </View>
            </View>
          ) : null}

          {article.video_attachments.length > 0 ? (
            <View style={styles.mediaSection}>
              <Text style={styles.mediaKicker}>Article Media</Text>
              <Text style={styles.mediaHeading}>Videos</Text>

              <View style={styles.videoList}>
                {article.video_attachments.map((video, index) => (
                  <Pressable
                    key={video.id}
                    style={styles.videoButton}
                    onPress={() => Linking.openURL(video.video_url)}
                  >
                    <Text style={styles.videoButtonTitle}>
                      Open video {index + 1}
                    </Text>
                    {video.caption ? (
                      <Text style={styles.videoButtonCaption}>
                        {video.caption}
                      </Text>
                    ) : null}
                  </Pressable>
                ))}
              </View>
            </View>
          ) : null}

          {article.tags.length > 0 ? (
            <View style={styles.tags}>
              {article.tags.map((tag) => (
                <Text key={tag.slug} style={styles.tag}>
                  {tag.name}
                </Text>
              ))}
            </View>
          ) : null}

          {error ? (
            <Text style={styles.engagementError}>{error}</Text>
          ) : null}

          <View style={styles.engagement}>
            <View style={styles.stats}>
              <Text style={styles.stat}>
                <Text style={styles.statStrong}>{article.engagement.views}</Text>{" "}
                views
              </Text>
              <Text style={styles.stat}>
                <Text style={styles.statStrong}>
                  {article.engagement.reactions}
                </Text>{" "}
                reactions
              </Text>
              <Text style={styles.stat}>
                <Text style={styles.statStrong}>{article.engagement.shares}</Text>{" "}
                shares
              </Text>
            </View>

            <View style={styles.actions}>
              <Pressable
                style={[
                  styles.secondaryAction,
                  data?.has_reacted && styles.actionDisabled,
                ]}
                onPress={reactArticle}
                disabled={reacting || data?.has_reacted}
              >
                <Text style={styles.secondaryActionText}>
                  {data?.has_reacted
                    ? "Reacted"
                    : reacting
                      ? "Reacting…"
                      : "React"}
                </Text>
              </Pressable>

              <Pressable
                style={[
                  styles.secondaryAction,
                  data?.has_shared && styles.actionDisabled,
                ]}
                onPress={shareArticle}
                disabled={sharing}
              >
                <Text style={styles.secondaryActionText}>
                  {sharing ? "Sharing…" : "Share"}
                </Text>
              </Pressable>

              <Pressable style={styles.primaryAction} onPress={downloadPdf}>
                <Text style={styles.primaryActionText}>Download PDF</Text>
              </Pressable>
            </View>
          </View>
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.white,
  },
  scroll: {
    flex: 1,
    backgroundColor: colors.white,
  },
  content: {
    paddingHorizontal: 16,
    paddingTop: 27,
    paddingBottom: 58,
  },
  header: {
    paddingBottom: 23,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  category: {
    marginBottom: 10,
    color: colors.gold,
    fontSize: 12,
    fontWeight: "800",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 42,
    lineHeight: 44,
    fontWeight: "700",
    letterSpacing: -0.6,
  },
  subtitle: {
    marginTop: 16,
    color: "#4b5651",
    fontFamily: typography.serif,
    fontSize: 21,
    lineHeight: 30,
  },
  byline: {
    marginTop: 22,
    gap: 10,
  },
  bylineCopy: {
    gap: 6,
  },
  bylineText: {
    color: colors.muted,
    fontSize: 13,
  },
  bylineStrong: {
    fontWeight: "800",
    color: colors.ink,
  },
  contributorList: {
    gap: 4,
  },
  contributor: {
    color: colors.muted,
    fontSize: 11.5,
  },
  date: {
    color: colors.muted,
    fontSize: 12.5,
  },
  featuredFigure: {
    marginTop: 28,
  },
  featuredImage: {
    width: "100%",
    aspectRatio: 16 / 10,
    borderRadius: 8,
    backgroundColor: "#f1f3f2",
  },
  captionRow: {
    marginTop: 8,
    gap: 2,
  },
  caption: {
    color: colors.muted,
    fontSize: 11.5,
    lineHeight: 17,
  },
  credit: {
    color: colors.muted,
    fontSize: 11.5,
    lineHeight: 17,
    fontStyle: "italic",
  },
  standfirst: {
    marginTop: 28,
    color: "#3c4842",
    fontFamily: typography.serif,
    fontSize: 20,
    lineHeight: 31,
    fontWeight: "700",
  },
  body: {
    marginTop: 28,
    color: "#202a25",
    fontFamily: typography.serif,
    fontSize: 18,
    lineHeight: 33,
  },
  mediaSection: {
    marginTop: 42,
    paddingTop: 22,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
  mediaKicker: {
    color: colors.gold,
    fontSize: 10.5,
    fontWeight: "800",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  mediaHeading: {
    marginTop: 4,
    marginBottom: 16,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 28,
    fontWeight: "700",
  },
  gallery: {
    gap: 18,
  },
  galleryItem: {
    gap: 2,
  },
  galleryImage: {
    width: "100%",
    aspectRatio: 4 / 3,
    borderRadius: 8,
    backgroundColor: colors.soft,
  },
  videoList: {
    gap: 12,
  },
  videoButton: {
    padding: 15,
    borderRadius: 8,
    backgroundColor: "#111815",
  },
  videoButtonTitle: {
    color: colors.white,
    fontWeight: "800",
  },
  videoButtonCaption: {
    marginTop: 4,
    color: "#dce4df",
    fontSize: 12,
  },
  tags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginTop: 34,
    paddingTop: 18,
    borderTopWidth: 1,
    borderTopColor: colors.line,
  },
  tag: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: colors.soft,
    color: colors.green,
    fontSize: 12,
    fontWeight: "700",
  },
  engagement: {
    marginTop: 26,
    paddingVertical: 18,
    gap: 16,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.line,
  },
  stats: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 14,
  },
  stat: {
    color: colors.muted,
    fontSize: 12.5,
  },
  statStrong: {
    color: colors.green,
    fontWeight: "800",
  },
  actions: {
    flexDirection: "row",
    gap: 8,
  },
  secondaryAction: {
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 999,
    backgroundColor: colors.white,
  },
  secondaryActionText: {
    color: colors.green,
    fontSize: 12.5,
    fontWeight: "700",
  },
  primaryAction: {
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.green,
    borderRadius: 999,
    backgroundColor: colors.green,
  },
  primaryActionText: {
    color: colors.white,
    fontSize: 12.5,
    fontWeight: "700",
  },

  actionDisabled: {
    opacity: 0.58,
  },
  engagementError: {
    color: "#b42318",
    fontSize: 13,
    lineHeight: 18,
    marginTop: 14,
  },
});
