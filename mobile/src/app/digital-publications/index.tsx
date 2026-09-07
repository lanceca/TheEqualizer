import { useCallback, useEffect, useState } from "react";
import {
  Image,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import { ScreenState } from "../../components/ScreenState";
import { SiteHeader } from "../../components/SiteHeader";
import {
  apiGet,
  formatDate,
  truncateWords,
} from "../../lib/api";
import type { DigitalPublicationsResponse } from "../../lib/types";
import { colors, typography } from "../../theme";

export default function DigitalPublicationsScreen() {
  const [data, setData] =
    useState<DigitalPublicationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");

    try {
      setData(
        await apiGet<DigitalPublicationsResponse>(
          "/digital-publications/"
        )
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load digital publications."
      );
    } finally {
      refresh ? setRefreshing(false) : setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const publications = data?.digital_publications ?? [];

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ScreenState loading message="Loading digital publications…" />
      ) : error && !data ? (
        <ScreenState message={error} onRetry={() => load()} />
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => load(true)}
              tintColor={colors.green}
            />
          }
        >
          <View style={styles.header}>
            <Text style={styles.kicker}>The Equalizer</Text>
            <Text style={styles.title}>Digital Publications</Text>
            <Text style={styles.description}>
              Browse complete PDF issues of The Equalizer student publication
              and open any issue in the interactive page-flipping reader.
            </Text>
            <Text style={styles.count}>
              {publications.length}{" "}
              {publications.length === 1 ? "publication" : "publications"}
            </Text>
          </View>

          {publications.length > 0 ? (
            <View style={styles.list}>
              {publications.map((publication) => (
                <Pressable
                  key={publication.id}
                  style={styles.card}
                  onPress={() =>
                    router.push({
                      pathname: "/digital-publications/[slug]",
                      params: { slug: publication.slug },
                    })
                  }
                >
                  {publication.cover_image_url ? (
                    <Image
                      source={{ uri: publication.cover_image_url }}
                      style={styles.cover}
                      resizeMode="cover"
                    />
                  ) : (
                    <View style={[styles.cover, styles.placeholder]}>
                      <Text style={styles.placeholderText}>The Equalizer</Text>
                    </View>
                  )}

                  <View style={styles.cardBody}>
                    <Text style={styles.cardTitle}>
                      {publication.title}
                    </Text>

                    <Text style={styles.meta}>
                      {formatDate(publication.publication_date)}
                      {publication.page_count
                        ? `  ·  ${publication.page_count} pages`
                        : ""}
                    </Text>

                    {publication.volume || publication.issue_number ? (
                      <Text style={styles.meta}>
                        {[publication.volume, publication.issue_number]
                          .filter(Boolean)
                          .join("  ·  ")}
                      </Text>
                    ) : null}

                    {publication.description ? (
                      <Text style={styles.cardDescription} numberOfLines={3}>
                        {truncateWords(publication.description, 24)}
                      </Text>
                    ) : null}

                    <Text style={styles.openLink}>
                      Open publication →
                    </Text>
                  </View>
                </Pressable>
              ))}
            </View>
          ) : (
            <View style={styles.empty}>
              <Text style={styles.emptyText}>
                No Digital Publications have been published yet.
              </Text>
            </View>
          )}
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
    paddingBottom: 56,
  },
  header: {
    paddingBottom: 18,
    marginBottom: 22,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  kicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.25,
    textTransform: "uppercase",
  },
  title: {
    marginTop: 4,
    color: colors.green,
    fontFamily: typography.serif,
    fontSize: 40,
    lineHeight: 44,
    fontWeight: "700",
  },
  description: {
    marginTop: 8,
    color: colors.muted,
    lineHeight: 22,
  },
  count: {
    marginTop: 11,
    color: colors.muted,
    fontSize: 12,
    fontWeight: "700",
  },
  list: {
    gap: 18,
  },
  card: {
    minHeight: 168,
    flexDirection: "row",
    overflow: "hidden",
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    backgroundColor: colors.white,
  },
  cover: {
    width: 112,
    minHeight: 168,
    backgroundColor: "#edf1ee",
  },
  placeholder: {
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  placeholderText: {
    color: colors.muted,
    fontFamily: typography.serif,
    fontWeight: "700",
    textAlign: "center",
  },
  cardBody: {
    flex: 1,
    minWidth: 0,
    paddingHorizontal: 15,
    paddingTop: 14,
    paddingBottom: 14,
  },
  cardTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 20,
    lineHeight: 23,
    fontWeight: "700",
  },
  meta: {
    marginTop: 6,
    color: colors.muted,
    fontSize: 11.5,
  },
  cardDescription: {
    marginTop: 9,
    color: "#46534d",
    fontSize: 13,
    lineHeight: 19,
  },
  openLink: {
    marginTop: 12,
    color: colors.green,
    fontSize: 12.5,
    fontWeight: "800",
  },
  empty: {
    paddingHorizontal: 20,
    paddingVertical: 44,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.soft,
  },
  emptyText: {
    color: colors.muted,
    textAlign: "center",
  },
});
