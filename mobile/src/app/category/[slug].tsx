import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useLocalSearchParams } from "expo-router";

import {
  CategoryFeaturedStory,
  StoryCard,
} from "../../components/ArticleCards";
import { ScreenState } from "../../components/ScreenState";
import { SectionHeading } from "../../components/SectionHeading";
import { SiteHeader } from "../../components/SiteHeader";
import { apiGet } from "../../lib/api";
import type { ArticlesResponse, CategoriesResponse } from "../../lib/types";
import { colors, typography } from "../../theme";

export default function CategoryScreen() {
  const params = useLocalSearchParams<{ slug: string; title?: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;
  const titleParam = Array.isArray(params.title) ? params.title[0] : params.title;

  const [data, setData] = useState<ArticlesResponse | null>(null);
  const [categories, setCategories] = useState<CategoriesResponse | null>(null);
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const category = useMemo(
    () => categories?.categories.find((item) => item.slug === slug),
    [categories, slug]
  );

  const title = titleParam || category?.name || "Article Category";

  const load = useCallback(
    async (refresh = false, search = submittedQuery) => {
      if (!slug) return;

      refresh ? setRefreshing(true) : setLoading(true);
      setError("");

      try {
        const encodedSlug = encodeURIComponent(slug);
        const searchPart = search
          ? `&q=${encodeURIComponent(search)}`
          : "";

        const [articlesResponse, categoriesResponse] = await Promise.all([
          apiGet<ArticlesResponse>(
            `/articles/?category=${encodedSlug}&limit=100${searchPart}`
          ),
          apiGet<CategoriesResponse>("/categories/"),
        ]);

        setData(articlesResponse);
        setCategories(categoriesResponse);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load category articles."
        );
      } finally {
        refresh ? setRefreshing(false) : setLoading(false);
      }
    },
    [slug, submittedQuery]
  );

  useEffect(() => {
    load(false, submittedQuery);
  }, [load, submittedQuery]);

  const submitSearch = () => {
    setSubmittedQuery(query.trim());
  };

  const clearSearch = () => {
    setQuery("");
    setSubmittedQuery("");
  };

  const articles = data?.articles ?? [];
  const leadArticle = articles[0];
  const remainingArticles = articles.slice(1);

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ScreenState loading message={`Loading ${title}…`} />
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
            <Text style={styles.kicker}>Article Category</Text>
            <Text style={styles.heading}>{title}</Text>

            <Text style={styles.description}>
              {category?.description ||
                `Published stories from The Equalizer under ${title}.`}
            </Text>

            <Text style={styles.count}>
              {articles.length}{" "}
              {submittedQuery
                ? `result${articles.length === 1 ? "" : "s"}`
                : `published article${articles.length === 1 ? "" : "s"}`}
            </Text>

            {submittedQuery ? (
              <View style={styles.searchSummaryRow}>
                <Text style={styles.searchSummary}>
                  Search: “{submittedQuery}”
                </Text>
                <Pressable onPress={clearSearch}>
                  <Text style={styles.clearLink}>Clear</Text>
                </Pressable>
              </View>
            ) : null}
          </View>

          <View style={styles.searchBar}>
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder={`Search ${title}`}
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              onSubmitEditing={submitSearch}
              style={styles.searchInput}
            />
            <Pressable style={styles.searchButton} onPress={submitSearch}>
              <Text style={styles.searchButtonText}>Search</Text>
            </Pressable>
          </View>

          {leadArticle ? (
            <>
              <CategoryFeaturedStory article={leadArticle} />

              {remainingArticles.length > 0 ? (
                <View style={styles.moreSection}>
                  <SectionHeading
                    kicker={`More in ${title}`}
                    title="Latest Articles"
                  />

                  <View style={styles.cards}>
                    {remainingArticles.map((article) => (
                      <StoryCard key={article.id} article={article} />
                    ))}
                  </View>
                </View>
              ) : null}
            </>
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>
                {submittedQuery
                  ? `No ${title} articles matched “${submittedQuery}”`
                  : `No ${title} articles are published yet`}
              </Text>
              <Text style={styles.emptyText}>
                {submittedQuery
                  ? "Try another search term or clear the current search to view every published article in this category."
                  : "Published stories will appear here once they are released by The Equalizer."}
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
    paddingBottom: 16,
    marginBottom: 16,
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
  heading: {
    marginTop: 3,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 40,
    lineHeight: 43,
    fontWeight: "700",
  },
  description: {
    marginTop: 10,
    color: colors.muted,
    fontSize: 14,
    lineHeight: 22,
  },
  count: {
    marginTop: 12,
    color: colors.muted,
    fontSize: 12,
  },
  searchSummaryRow: {
    marginTop: 5,
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
  },
  searchSummary: {
    color: colors.muted,
    fontSize: 12,
  },
  clearLink: {
    color: colors.greenDeep,
    fontSize: 12,
    fontWeight: "800",
  },
  searchBar: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 20,
  },
  searchInput: {
    flex: 1,
    minHeight: 42,
    paddingHorizontal: 13,
    borderWidth: 1,
    borderColor: "#b9ccc3",
    borderRadius: 999,
    backgroundColor: colors.white,
    color: colors.green,
    fontSize: 13,
  },
  searchButton: {
    minHeight: 42,
    justifyContent: "center",
    paddingHorizontal: 16,
    borderRadius: 999,
    backgroundColor: colors.green,
  },
  searchButtonText: {
    color: colors.white,
    fontSize: 13,
    fontWeight: "800",
  },
  moreSection: {
    marginTop: 38,
  },
  cards: {
    gap: 18,
  },
  emptyState: {
    paddingHorizontal: 22,
    paddingVertical: 48,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    backgroundColor: colors.soft,
    alignItems: "center",
  },
  emptyTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 24,
    fontWeight: "700",
    textAlign: "center",
  },
  emptyText: {
    marginTop: 9,
    color: colors.muted,
    lineHeight: 21,
    textAlign: "center",
  },
});
