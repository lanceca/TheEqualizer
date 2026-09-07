import { useCallback, useEffect, useState } from "react";
import {
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { SchoolUpdateCard } from "../../components/SchoolUpdateCard";
import { ScreenState } from "../../components/ScreenState";
import { SiteHeader } from "../../components/SiteHeader";
import { apiGet } from "../../lib/api";
import type { SchoolUpdatesResponse } from "../../lib/types";
import { colors, typography } from "../../theme";

export default function SchoolUpdatesScreen() {
  const [data, setData] = useState<SchoolUpdatesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");

    try {
      setData(
        await apiGet<SchoolUpdatesResponse>("/school-updates/")
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load school updates."
      );
    } finally {
      refresh ? setRefreshing(false) : setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updates = data?.school_updates ?? [];

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ScreenState loading message="Loading school updates…" />
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
            <Text style={styles.kicker}>Campus Notices</Text>
            <Text style={styles.title}>School Updates</Text>
            <Text style={styles.description}>
              School-related announcements, programs, opportunities, events,
              and other public information curated by The Equalizer.
            </Text>
          </View>

          {updates.length > 0 ? (
            <View style={styles.grid}>
              {updates.map((update) => (
                <SchoolUpdateCard key={update.id} update={update} />
              ))}
            </View>
          ) : (
            <View style={styles.empty}>
              <Text style={styles.emptyTitle}>
                No school updates are currently posted
              </Text>
              <Text style={styles.emptyText}>
                New school-related announcements will appear here when they
                are published by The Equalizer.
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
    fontSize: 40,
    fontWeight: "700",
  },
  description: {
    marginTop: 8,
    color: colors.muted,
    fontSize: 14,
    lineHeight: 23,
  },
  grid: {
    gap: 20,
  },
  empty: {
    paddingHorizontal: 20,
    paddingVertical: 45,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    backgroundColor: colors.soft,
    alignItems: "center",
  },
  emptyTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 23,
    fontWeight: "700",
    textAlign: "center",
  },
  emptyText: {
    marginTop: 8,
    color: colors.muted,
    lineHeight: 21,
    textAlign: "center",
  },
});
