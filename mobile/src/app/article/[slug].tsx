import { useCallback, useEffect, useState } from "react";
import {
  Image,
  Linking,
  Modal,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams } from "expo-router";

import { ScreenState } from "../../components/ScreenState";
import { ArticleDetailSkeleton } from "../../components/SkeletonLayouts";
import { SiteHeader } from "../../components/SiteHeader";
import {
  SITE_ORIGIN,
  apiGet,
  apiPost,
  formatDate,
  formatTime,
  stripHtml,
} from "../../lib/api";
import type {
  ArticleContributor,
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
  const [expandedImage, setExpandedImage] = useState<{
    uri: string;
    caption: string;
    credit: string;
  } | null>(null);

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
      setError(err instanceof Error ? err.message : "Unable to load article.");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const article = data?.article;

  const reactArticle = async () => {
    if (!article || reacting) return;
    setReacting(true);

    try {
      const response = await apiPost<ArticleEngagementActionResponse>(
        `/articles/${encodeURIComponent(article.slug)}/react/`
      );

      setData((current) =>
        current
          ? {
              ...current,
              has_reacted: response.has_reacted ?? false,
              article: {
                ...current.article,
                engagement: response.engagement,
              },
            }
          : current
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update like.");
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
      setError(err instanceof Error ? err.message : "Unable to share this article.");
    } finally {
      setSharing(false);
    }
  };

  const openVersionHistory = () => {
    if (article?.version_history_url) {
      Linking.openURL(article.version_history_url);
    }
  };

  const downloadPdf = () => {
    if (!article) return;
    Linking.openURL(
      article.pdf_url || `${SITE_ORIGIN}/articles/${article.slug}/download-pdf/`
    );
  };

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !article ? (
        <ArticleDetailSkeleton />
      ) : error && !article ? (
        <ScreenState message={error} onRetry={load} />
      ) : !article ? (
        <ScreenState message="Article not found." />
      ) : (
        <ScrollView style={styles.scroll} contentContainerStyle={styles.content}>
          {article.is_archived ? (
            <View style={styles.archiveNotice}>
              <Text style={styles.archiveNoticeKicker}>Publication Archive</Text>
              <Text style={styles.archiveNoticeText}>
                This story is part of The Equalizer's public archive and is no longer in the active publication feed.
              </Text>
            </View>
          ) : null}

          <View style={styles.header}>
            <Text style={styles.category}>{article.category.name}</Text>
            <Text style={styles.title}>{article.title}</Text>

            {article.subtitle ? (
              <Text style={styles.subtitle}>{article.subtitle}</Text>
            ) : null}

            <View style={styles.creditSection}>
              <ProfileCredit
                imageUrl={article.author.profile_picture_url}
                name={article.author.display_name}
                handle={`@${article.author.username}`}
                label="Written by"
              />

              {article.contributors.length > 0 ? (
                <View style={styles.contributorsSection}>
                  <Text style={styles.sectionLabel}>Contributors</Text>
                  <View style={styles.contributorGrid}>
                    {article.contributors.map((contributor, index) => (
                      <ContributorCard
                        key={`${contributor.username}-${contributor.role}-${index}`}
                        contributor={contributor}
                      />
                    ))}
                  </View>
                </View>
              ) : null}
            </View>

            <View style={styles.publicationCard}>
              <Text style={styles.publicationKicker}>
                {article.is_archived ? "Originally published" : "Published"}
              </Text>
              <Text style={styles.publicationDate}>
                {formatDate(article.published_at)}
              </Text>
              <Text style={styles.publicationTime}>
                {formatTime(article.published_at)}
              </Text>

              <View style={styles.publicationDivider} />

              <View style={styles.versionRow}>
                <View style={styles.versionBadge}>
                  <Text style={styles.versionBadgeText}>
                    Version {article.version_number}
                  </Text>
                </View>

                <Pressable
                  style={styles.versionButton}
                  onPress={openVersionHistory}
                >
                  <Text style={styles.versionButtonText}>Version history</Text>
                </Pressable>
              </View>
            </View>
          </View>

          {article.featured_image_url ? (
            <View style={styles.featuredFigure}>
              <Pressable
                style={({ pressed }) => [
                  styles.expandableImageButton,
                  pressed && styles.expandableImagePressed,
                ]}
                onPress={() =>
                  setExpandedImage({
                    uri: article.featured_image_url,
                    caption: article.featured_image_caption || "",
                    credit: article.featured_image_credit || "",
                  })
                }
                accessibilityRole="button"
                accessibilityLabel="Expand featured image"
              >
                <Image
                  source={{ uri: article.featured_image_url }}
                  style={styles.featuredImage}
                  resizeMode="contain"
                />
                <View style={styles.expandHint}>
                  <Text style={styles.expandHintText}>Tap to expand</Text>
                </View>
              </Pressable>

              {article.featured_image_caption || article.featured_image_credit ? (
                <View style={styles.captionRow}>
                  {article.featured_image_caption ? (
                    <Text style={styles.caption}>{article.featured_image_caption}</Text>
                  ) : null}
                  {article.featured_image_credit ? (
                    <Text style={styles.credit}>{article.featured_image_credit}</Text>
                  ) : null}
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
                    <Pressable
                      style={({ pressed }) => [
                        styles.expandableImageButton,
                        pressed && styles.expandableImagePressed,
                      ]}
                      onPress={() =>
                        setExpandedImage({
                          uri: attachment.image_url,
                          caption: attachment.caption || "",
                          credit: attachment.credit || "",
                        })
                      }
                      accessibilityRole="button"
                      accessibilityLabel={
                        attachment.caption
                          ? `Expand image: ${attachment.caption}`
                          : "Expand article image"
                      }
                    >
                      <Image
                        source={{ uri: attachment.image_url }}
                        style={styles.galleryImage}
                        resizeMode="cover"
                      />
                      <View style={styles.expandHint}>
                        <Text style={styles.expandHintText}>Tap to expand</Text>
                      </View>
                    </Pressable>

                    {attachment.caption || attachment.credit ? (
                      <View style={styles.captionRow}>
                        {attachment.caption ? (
                          <Text style={styles.caption}>{attachment.caption}</Text>
                        ) : null}
                        {attachment.credit ? (
                          <Text style={styles.credit}>{attachment.credit}</Text>
                        ) : null}
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
                    <Text style={styles.videoButtonTitle}>Open video {index + 1}</Text>
                    {video.caption ? (
                      <Text style={styles.videoButtonCaption}>{video.caption}</Text>
                    ) : null}
                    {video.credit ? (
                      <Text style={styles.videoButtonCredit}>{video.credit}</Text>
                    ) : null}
                  </Pressable>
                ))}
              </View>
            </View>
          ) : null}

          {article.tags.length > 0 ? (
            <View style={styles.tags}>
              {article.tags.map((tag) => (
                <Text key={tag.slug} style={styles.tag}>{tag.name}</Text>
              ))}
            </View>
          ) : null}

          {error ? <Text style={styles.engagementError}>{error}</Text> : null}

          <View style={styles.engagement}>
            <View style={styles.stats}>
              <Metric value={article.engagement.views} label="views" />
              <Metric
                value={article.engagement.reactions}
                label={article.engagement.reactions === 1 ? "like" : "likes"}
              />
              <Metric value={article.engagement.shares} label="shares" />
              <Metric
                value={article.engagement.downloads ?? 0}
                label={(article.engagement.downloads ?? 0) === 1 ? "PDF download" : "PDF downloads"}
              />
            </View>

            <View style={styles.actions}>
              <Pressable
                style={styles.secondaryAction}
                onPress={reactArticle}
                disabled={reacting}
              >
                <Text style={styles.secondaryActionText}>
                  {reacting
                    ? data?.has_reacted
                      ? "Unliking…"
                      : "Liking…"
                    : data?.has_reacted
                      ? "Unlike"
                      : "Like"}
                </Text>
              </Pressable>

              <Pressable
                style={styles.secondaryAction}
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

      <Modal
        visible={Boolean(expandedImage)}
        transparent
        animationType="fade"
        statusBarTranslucent
        onRequestClose={() => setExpandedImage(null)}
      >
        <View style={styles.imageViewerBackdrop}>
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={() => setExpandedImage(null)}
            accessibilityRole="button"
            accessibilityLabel="Close expanded image"
          />

          <View style={styles.imageViewerContent}>
            <Pressable
              style={styles.imageViewerClose}
              onPress={() => setExpandedImage(null)}
              accessibilityRole="button"
              accessibilityLabel="Close expanded image"
            >
              <Text style={styles.imageViewerCloseText}>×</Text>
            </Pressable>

            {expandedImage ? (
              <>
                <Image
                  source={{ uri: expandedImage.uri }}
                  style={styles.imageViewerImage}
                  resizeMode="contain"
                />

                {expandedImage.caption || expandedImage.credit ? (
                  <View style={styles.imageViewerCaptionPanel}>
                    {expandedImage.caption ? (
                      <Text style={styles.imageViewerCaption}>{expandedImage.caption}</Text>
                    ) : null}
                    {expandedImage.credit ? (
                      <Text style={styles.imageViewerCredit}>{expandedImage.credit}</Text>
                    ) : null}
                  </View>
                ) : null}
              </>
            ) : null}
          </View>
        </View>
      </Modal>
    </View>
  );
}

function ProfileCredit({
  imageUrl,
  name,
  handle,
  label,
}: {
  imageUrl: string;
  name: string;
  handle: string;
  label: string;
}) {
  return (
    <View style={styles.profileCredit}>
      <Avatar imageUrl={imageUrl} name={name} size={56} />
      <View style={styles.profileCreditCopy}>
        <Text style={styles.sectionLabel}>{label}</Text>
        <Text style={styles.profileName}>{name}</Text>
        <Text style={styles.profileHandle}>{handle}</Text>
      </View>
    </View>
  );
}

function ContributorCard({ contributor }: { contributor: ArticleContributor }) {
  return (
    <View style={styles.contributorCard}>
      <Avatar
        imageUrl={contributor.profile_picture_url}
        name={contributor.display_name}
        size={40}
      />
      <View style={styles.contributorCopy}>
        <Text style={styles.contributorRole}>{contributor.role_display}</Text>
        <Text style={styles.contributorName}>{contributor.display_name}</Text>
        <Text style={styles.contributorHandle}>@{contributor.username}</Text>
      </View>
    </View>
  );
}

function Avatar({ imageUrl, name, size }: { imageUrl: string; name: string; size: number }) {
  const initial = (name || "?").trim().charAt(0).toUpperCase() || "?";

  return imageUrl ? (
    <Image
      source={{ uri: imageUrl }}
      style={{ width: size, height: size, borderRadius: size / 2 }}
      resizeMode="cover"
    />
  ) : (
    <View
      style={[
        styles.avatarPlaceholder,
        { width: size, height: size, borderRadius: size / 2 },
      ]}
    >
      <Text style={[styles.avatarInitial, { fontSize: Math.max(14, size * 0.36) }]}>
        {initial}
      </Text>
    </View>
  );
}

function Metric({ value, label }: { value: number; label: string }) {
  return (
    <Text style={styles.stat}>
      <Text style={styles.statStrong}>{value}</Text> {label}
    </Text>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.white },
  scroll: { flex: 1, backgroundColor: colors.white },
  content: { paddingHorizontal: 16, paddingTop: 24, paddingBottom: 58 },
  archiveNotice: {
    marginBottom: 20,
    padding: 14,
    borderWidth: 1,
    borderColor: "#d9c36f",
    borderRadius: 12,
    backgroundColor: "#fffaf0",
  },
  archiveNoticeKicker: {
    color: "#6d5717",
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  archiveNoticeText: { marginTop: 5, color: "#5d532f", fontSize: 12.5, lineHeight: 19 },
  header: { paddingBottom: 24, borderBottomWidth: 1, borderBottomColor: colors.line },
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
    lineHeight: 45,
    fontWeight: "700",
    letterSpacing: -0.6,
  },
  subtitle: {
    marginTop: 15,
    color: "#4b5651",
    fontFamily: typography.serif,
    fontSize: 21,
    lineHeight: 30,
  },
  creditSection: { marginTop: 23 },
  profileCredit: { flexDirection: "row", alignItems: "center", gap: 13 },
  profileCreditCopy: { flex: 1 },
  sectionLabel: {
    color: "#8b762e",
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  profileName: {
    marginTop: 2,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 19,
    fontWeight: "700",
  },
  profileHandle: { marginTop: 2, color: "#78847e", fontSize: 11 },
  avatarPlaceholder: {
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#d8e4dd",
    backgroundColor: "#edf4f0",
  },
  avatarInitial: { color: colors.greenDeep, fontFamily: typography.serif, fontWeight: "700" },
  contributorsSection: {
    marginTop: 17,
    paddingTop: 14,
    borderTopWidth: 1,
    borderTopColor: "#edf1ee",
  },
  contributorGrid: { gap: 8, marginTop: 8 },
  contributorCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 9,
    padding: 9,
    borderWidth: 1,
    borderColor: "#e0e7e3",
    borderRadius: 10,
    backgroundColor: "#fafcfb",
  },
  contributorCopy: { flex: 1 },
  contributorRole: {
    color: "#8b762e",
    fontSize: 8.5,
    fontWeight: "900",
    letterSpacing: 0.6,
    textTransform: "uppercase",
  },
  contributorName: { marginTop: 2, color: colors.greenDeep, fontSize: 12.5, fontWeight: "800" },
  contributorHandle: { marginTop: 1, color: "#7b8781", fontSize: 9.5 },
  publicationCard: {
    marginTop: 20,
    padding: 16,
    borderWidth: 1,
    borderLeftWidth: 4,
    borderColor: "#d8e2dc",
    borderLeftColor: colors.gold,
    borderRadius: 12,
    backgroundColor: "#fbfcfb",
  },
  publicationKicker: {
    color: "#8b762e",
    fontSize: 9,
    fontWeight: "900",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  publicationDate: {
    marginTop: 4,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 20,
    fontWeight: "700",
  },
  publicationTime: { marginTop: 3, color: "#6e7b75", fontSize: 11, fontWeight: "600" },
  publicationDivider: { height: 1, marginVertical: 12, backgroundColor: "#edf0ee" },
  versionRow: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  versionBadge: {
    minHeight: 32,
    justifyContent: "center",
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: "#d9c36f",
    borderRadius: 999,
    backgroundColor: "#fffaf0",
  },
  versionBadgeText: { color: "#6d5717", fontSize: 10, fontWeight: "850" },
  versionButton: {
    minHeight: 32,
    justifyContent: "center",
    paddingHorizontal: 10,
    borderWidth: 1,
    borderColor: "#cfdad4",
    borderRadius: 999,
    backgroundColor: colors.white,
  },
  versionButtonText: { color: colors.green, fontSize: 10, fontWeight: "850" },
  featuredFigure: { marginTop: 28 },
  featuredImage: {
    width: "100%",
    aspectRatio: 16 / 10,
    borderRadius: 8,
    backgroundColor: "#f1f3f2",
  },
  expandableImageButton: { position: "relative", overflow: "hidden", borderRadius: 8 },
  expandableImagePressed: { opacity: 0.88 },
  expandHint: {
    position: "absolute",
    right: 10,
    bottom: 10,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: "rgba(15, 45, 36, 0.82)",
  },
  expandHintText: { color: colors.white, fontSize: 10.5, fontWeight: "800" },
  captionRow: { marginTop: 8, gap: 2 },
  caption: { color: colors.muted, fontSize: 11.5, lineHeight: 17 },
  credit: { color: colors.muted, fontSize: 11.5, lineHeight: 17, fontStyle: "italic" },
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
  mediaSection: { marginTop: 42, paddingTop: 22, borderTopWidth: 1, borderTopColor: colors.line },
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
  gallery: { gap: 18 },
  galleryItem: { gap: 2 },
  galleryImage: { width: "100%", aspectRatio: 4 / 3, borderRadius: 8, backgroundColor: colors.soft },
  videoList: { gap: 12 },
  videoButton: { padding: 15, borderRadius: 8, backgroundColor: "#111815" },
  videoButtonTitle: { color: colors.white, fontWeight: "800" },
  videoButtonCaption: { marginTop: 4, color: "#dce4df", fontSize: 12 },
  videoButtonCredit: { marginTop: 3, color: "#b8c4be", fontSize: 11, fontStyle: "italic" },
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
  stats: { flexDirection: "row", flexWrap: "wrap", gap: 14 },
  stat: { color: colors.muted, fontSize: 12.5 },
  statStrong: { color: colors.green, fontWeight: "800" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  secondaryAction: {
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 999,
    backgroundColor: colors.white,
  },
  secondaryActionText: { color: colors.green, fontSize: 12.5, fontWeight: "700" },
  primaryAction: {
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.green,
    borderRadius: 999,
    backgroundColor: colors.green,
  },
  primaryActionText: { color: colors.white, fontSize: 12.5, fontWeight: "700" },
  engagementError: { color: "#b42318", fontSize: 13, lineHeight: 18, marginTop: 14 },
  imageViewerBackdrop: { flex: 1, backgroundColor: "rgba(4, 9, 7, 0.96)" },
  imageViewerContent: {
    flex: 1,
    width: "100%",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 16,
    paddingTop: 54,
    paddingBottom: 28,
  },
  imageViewerClose: {
    position: "absolute",
    top: 48,
    right: 18,
    zIndex: 2,
    width: 42,
    height: 42,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 21,
    backgroundColor: "rgba(255, 255, 255, 0.14)",
  },
  imageViewerCloseText: { color: colors.white, fontSize: 30, lineHeight: 32, fontWeight: "400" },
  imageViewerImage: { width: "100%", height: "78%" },
  imageViewerCaptionPanel: { width: "100%", maxWidth: 720, marginTop: 16, paddingHorizontal: 4, gap: 4 },
  imageViewerCaption: { color: colors.white, fontSize: 13, lineHeight: 19, textAlign: "center" },
  imageViewerCredit: { color: "#c8d2cd", fontSize: 12, lineHeight: 18, fontStyle: "italic", textAlign: "center" },
});
