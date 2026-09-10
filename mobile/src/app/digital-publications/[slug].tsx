import { useCallback, useEffect, useState } from "react";
import {
  Image,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams } from "expo-router";
import * as WebBrowser from "expo-web-browser";

import { ScreenState } from "../../components/ScreenState";
import { SiteHeader } from "../../components/SiteHeader";
import {
  SITE_ORIGIN,
  apiGet,
  formatDate,
} from "../../lib/api";
import type { DigitalPublicationDetailResponse } from "../../lib/types";
import { colors, typography } from "../../theme";

export default function DigitalPublicationDetailScreen() {
  const params = useLocalSearchParams<{ slug: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;

  const [data, setData] =
    useState<DigitalPublicationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!slug) return;

    setLoading(true);
    setError("");

    try {
      setData(
        await apiGet<DigitalPublicationDetailResponse>(
          `/digital-publications/${encodeURIComponent(slug)}/`
        )
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load publication."
      );
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const publication = data?.digital_publication;

  const openInteractive = async () => {
    if (!publication) return;

    await WebBrowser.openBrowserAsync(
      `${SITE_ORIGIN}/digital-publications/${publication.slug}/`
    );
  };

  const openPdf = () => {
    if (publication?.pdf_url) {
      Linking.openURL(publication.pdf_url);
    }
  };

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !publication ? (
        <ScreenState loading message="Loading publication…" />
      ) : error && !publication ? (
        <ScreenState message={error} onRetry={load} />
      ) : !publication ? (
        <ScreenState message="Publication not found." />
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
        >
          <Text style={styles.kicker}>The Equalizer</Text>
          <Text style={styles.title}>{publication.title}</Text>

          <View style={styles.metaWrap}>
            <Text style={styles.meta}>
              {formatDate(publication.publication_date)}
            </Text>

            {publication.page_count ? (
              <Text style={styles.meta}>
                {publication.page_count} pages
              </Text>
            ) : null}

            {publication.volume ? (
              <Text style={styles.meta}>{publication.volume}</Text>
            ) : null}

            {publication.issue_number ? (
              <Text style={styles.meta}>{publication.issue_number}</Text>
            ) : null}
          </View>

          {publication.cover_image_url ? (
            <Image
              source={{ uri: publication.cover_image_url }}
              style={styles.cover}
              resizeMode="contain"
            />
          ) : null}

          {publication.description ? (
            <Text style={styles.description}>
              {publication.description}
            </Text>
          ) : null}

          <View style={styles.orientationTip}>
            <Text style={styles.orientationTipTitle}>
              Best viewing on mobile
            </Text>

            <Text style={styles.orientationTipText}>
              For the best publication booklet experience, open the
              interactive reader and rotate your phone to landscape
              orientation.
            </Text>
          </View>

          <Pressable style={styles.primaryButton} onPress={openInteractive}>
            <Text style={styles.primaryButtonText}>
              Read interactive booklet
            </Text>
          </Pressable>

          {publication.pdf_url ? (
            <Pressable style={styles.secondaryButton} onPress={openPdf}>
              <Text style={styles.secondaryButtonText}>
                Open PDF directly
              </Text>
            </Pressable>
          ) : null}
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
    paddingTop: 28,
    paddingBottom: 56,
  },
  kicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.25,
    textTransform: "uppercase",
  },
  title: {
    marginTop: 5,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 38,
    lineHeight: 42,
    fontWeight: "700",
  },
  metaWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginTop: 12,
  },
  meta: {
    color: colors.muted,
    fontSize: 12,
  },
  cover: {
    width: "100%",
    height: 430,
    marginTop: 22,
    borderRadius: 12,
    backgroundColor: "#edf1ee",
  },
  description: {
    marginTop: 22,
    color: "#46534d",
    fontSize: 15,
    lineHeight: 24,
  },
  orientationTip: {
    marginTop: 22,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: "#d9c170",
    borderRadius: 12,
    backgroundColor: "#fff9e9",
  },
  orientationTipTitle: {
    color: "#3f3210",
    fontSize: 13,
    fontWeight: "800",
  },
  orientationTipText: {
    marginTop: 5,
    color: "#5d4a16",
    fontSize: 13,
    lineHeight: 20,
  },
  primaryButton: {
    marginTop: 18,
    minHeight: 46,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 999,
    backgroundColor: colors.green,
    paddingHorizontal: 18,
  },
  primaryButtonText: {
    color: colors.white,
    fontSize: 13.5,
    fontWeight: "800",
  },
  secondaryButton: {
    marginTop: 10,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.green,
    borderRadius: 999,
    backgroundColor: colors.white,
    paddingHorizontal: 18,
  },
  secondaryButtonText: {
    color: colors.green,
    fontSize: 13,
    fontWeight: "800",
  },
});
