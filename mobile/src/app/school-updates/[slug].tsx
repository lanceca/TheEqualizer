import { useCallback, useEffect, useState } from "react";
import {
  Image,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useLocalSearchParams } from "expo-router";

import { ScreenState } from "../../components/ScreenState";
import { SiteHeader } from "../../components/SiteHeader";
import { apiGet } from "../../lib/api";
import type { SchoolUpdateDetailResponse } from "../../lib/types";
import { colors, typography } from "../../theme";

export default function SchoolUpdateDetailScreen() {
  const params = useLocalSearchParams<{ slug: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;

  const [data, setData] =
    useState<SchoolUpdateDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!slug) return;

    setLoading(true);
    setError("");

    try {
      setData(
        await apiGet<SchoolUpdateDetailResponse>(
          `/school-updates/${encodeURIComponent(slug)}/`
        )
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load school update."
      );
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    load();
  }, [load]);

  const update = data?.school_update;

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !update ? (
        <ScreenState loading message="Loading school update…" />
      ) : error && !update ? (
        <ScreenState message={error} onRetry={load} />
      ) : !update ? (
        <ScreenState message="School update not found." />
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
        >
          <View style={styles.header}>
            <Text style={styles.kicker}>Campus Notices</Text>
            <Text style={styles.title}>{update.title}</Text>
            <Text style={styles.headerText}>
              School-related information selected by The Equalizer.
            </Text>
          </View>

          <View style={styles.card}>
            {update.image_url ? (
              <View style={styles.imageFrame}>
                <Image
                  source={{ uri: update.image_url }}
                  style={styles.image}
                  resizeMode="cover"
                />
              </View>
            ) : null}

            <View style={styles.body}>
              <Text style={styles.summary}>{update.summary}</Text>
              <Text style={styles.details}>{update.details}</Text>
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
    paddingHorizontal: 14,
    paddingTop: 28,
    paddingBottom: 50,
  },
  header: {
    paddingBottom: 18,
    marginBottom: 22,
    borderBottomWidth: 3,
    borderBottomColor: colors.green,
  },
  kicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.3,
    textTransform: "uppercase",
  },
  title: {
    marginTop: 4,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 38,
    lineHeight: 42,
    fontWeight: "700",
  },
  headerText: {
    marginTop: 8,
    color: colors.muted,
    lineHeight: 22,
  },
  card: {
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    backgroundColor: colors.white,
  },
  imageFrame: {
    marginHorizontal: 16,
    marginTop: 20,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.soft,
  },
  image: {
    width: "100%",
    aspectRatio: 16 / 10,
  },
  body: {
    paddingHorizontal: 20,
    paddingTop: 22,
    paddingBottom: 28,
  },
  summary: {
    marginBottom: 20,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 20,
    lineHeight: 31,
    fontWeight: "700",
  },
  details: {
    color: colors.ink,
    fontSize: 15,
    lineHeight: 27,
  },
});
