import { useCallback, useEffect, useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";

import {
  LeadStory,
  SecondaryStory,
  StoryCard,
} from "../components/ArticleCards";
import { SchoolUpdateCard } from "../components/SchoolUpdateCard";
import { ScreenState } from "../components/ScreenState";
import { SectionHeading } from "../components/SectionHeading";
import { SiteHeader } from "../components/SiteHeader";
import { apiGet } from "../lib/api";
import type { HomeResponse } from "../lib/types";
import { colors, typography } from "../theme";

export default function HomeScreen() {
  const [data, setData] = useState<HomeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");

    try {
      setData(await apiGet<HomeResponse>("/home/"));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load The Equalizer."
      );
    } finally {
      refresh ? setRefreshing(false) : setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const articles = data?.latest_articles ?? [];
  const leadArticle = articles[0];
  const secondaryArticles = articles.slice(1, 5);
  const moreArticles = articles.slice(5);
  const updates = data?.school_updates ?? [];

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ScreenState loading message="Loading The Equalizer…" />
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
          <SectionHeading
            kicker="Latest from The Equalizer"
            title="Top Stories"
            countText={
              articles.length
                ? `${articles.length} recent ${articles.length === 1 ? "story" : "stories"}`
                : undefined
            }
          />

          {leadArticle ? (
            <>
              <LeadStory article={leadArticle} />

              {secondaryArticles.length > 0 ? (
                <View style={styles.secondaryList}>
                  {secondaryArticles.map((article) => (
                    <SecondaryStory key={article.id} article={article} />
                  ))}
                </View>
              ) : null}

              {moreArticles.length > 0 ? (
                <View style={styles.moreSection}>
                  <SectionHeading
                    kicker="More Stories"
                    title="Keep Reading"
                  />

                  <View style={styles.cardList}>
                    {moreArticles.map((article) => (
                      <StoryCard key={article.id} article={article} />
                    ))}
                  </View>
                </View>
              ) : null}
            </>
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>No stories published yet</Text>
              <Text style={styles.emptyText}>
                Published articles will appear here once they are approved
                and released by The Equalizer.
              </Text>
            </View>
          )}

          <View style={styles.schoolSection}>
            <View style={styles.schoolHeading}>
              <Text style={styles.schoolKicker}>Campus Notices</Text>
              <Text style={styles.schoolTitle}>School Updates</Text>
              <Text style={styles.schoolDescription}>
                Announcements, programs, opportunities, and other
                school-related information selected by The Equalizer.
              </Text>
            </View>

            {updates.length > 0 ? (
              <View style={styles.schoolCards}>
                {updates.map((update) => (
                  <SchoolUpdateCard
                    key={update.id}
                    update={update}
                    compact
                  />
                ))}
              </View>
            ) : (
              <View style={styles.schoolEmpty}>
                <Text style={styles.schoolEmptyText}>
                  No school updates are currently posted.
                </Text>
              </View>
            )}

            <Pressable onPress={() => router.push("/school-updates" as never)}>
              <Text style={styles.allUpdates}>
                View all school updates
              </Text>
            </Pressable>
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
    paddingTop: 27,
    paddingBottom: 48,
  },
  secondaryList: {
    marginTop: 22,
    gap: 15,
  },
  moreSection: {
    marginTop: 38,
  },
  cardList: {
    gap: 18,
  },
  emptyState: {
    paddingHorizontal: 20,
    paddingVertical: 44,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 10,
    backgroundColor: colors.soft,
    alignItems: "center",
  },
  emptyTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 24,
    fontWeight: "700",
  },
  emptyText: {
    marginTop: 9,
    color: colors.muted,
    lineHeight: 21,
    textAlign: "center",
  },
  schoolSection: {
    marginTop: 42,
  },
  schoolHeading: {
    marginBottom: 14,
    padding: 18,
    borderWidth: 1,
    borderTopWidth: 4,
    borderColor: colors.line,
    borderTopColor: colors.gold,
    borderRadius: 12,
    backgroundColor: colors.soft,
  },
  schoolKicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.3,
    textTransform: "uppercase",
  },
  schoolTitle: {
    marginTop: 4,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 28,
    fontWeight: "700",
  },
  schoolDescription: {
    marginTop: 7,
    color: colors.muted,
    fontSize: 13,
    lineHeight: 20,
  },
  schoolCards: {
    gap: 16,
  },
  schoolEmpty: {
    padding: 18,
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.soft,
  },
  schoolEmptyText: {
    color: colors.muted,
    fontSize: 13,
    lineHeight: 20,
  },
  allUpdates: {
    marginTop: 14,
    color: colors.green,
    fontSize: 12.5,
    fontWeight: "800",
  },
});
