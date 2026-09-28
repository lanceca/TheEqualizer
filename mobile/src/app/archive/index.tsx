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

import { ArticleCard } from "../../components/ArticleCard";
import { ScreenState } from "../../components/ScreenState";
import { ArchiveSkeleton } from "../../components/SkeletonLayouts";
import { SiteHeader } from "../../components/SiteHeader";
import { apiGet, buildQueryString, formatMonthYear } from "../../lib/api";
import type {
  ArchiveResponse,
  ArticleSummary,
  CategoriesResponse,
} from "../../lib/types";
import { colors, typography } from "../../theme";

type AppliedFilters = {
  query: string;
  category: string;
  start: string;
  end: string;
};

const emptyFilters: AppliedFilters = {
  query: "",
  category: "",
  start: "",
  end: "",
};

export default function ArchiveScreen() {
  const [data, setData] = useState<ArchiveResponse | null>(null);
  const [categories, setCategories] = useState<CategoriesResponse | null>(null);
  const [query, setQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [applied, setApplied] = useState<AppliedFilters>(emptyFilters);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(
    async (refresh = false, filters = applied) => {
      refresh ? setRefreshing(true) : setLoading(true);
      setError("");

      try {
        const queryString = buildQueryString({
          limit: "200",
          q: filters.query,
          category: filters.category,
          start: filters.start,
          end: filters.end,
        });

        const [archiveResponse, categoriesResponse] = await Promise.all([
          apiGet<ArchiveResponse>(`/archive/?${queryString}`),
          apiGet<CategoriesResponse>("/categories/"),
        ]);

        setData(archiveResponse);
        setCategories(categoriesResponse);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load the publication archive."
        );
      } finally {
        refresh ? setRefreshing(false) : setLoading(false);
      }
    },
    [applied]
  );

  useEffect(() => {
    load(false, applied);
  }, [load, applied]);

  const applyFilters = () => {
    setApplied({
      query: query.trim(),
      category: selectedCategory,
      start: startDate.trim(),
      end: endDate.trim(),
    });
  };

  const clearFilters = () => {
    setQuery("");
    setSelectedCategory("");
    setStartDate("");
    setEndDate("");
    setApplied(emptyFilters);
  };

  const grouped = useMemo(() => {
    const groups: { label: string; articles: ArticleSummary[] }[] = [];

    for (const article of data?.articles ?? []) {
      const label = formatMonthYear(article.published_at);
      const last = groups[groups.length - 1];

      if (last?.label === label) {
        last.articles.push(article);
      } else {
        groups.push({ label, articles: [article] });
      }
    }

    return groups;
  }, [data]);

  const filterActive = Boolean(
    applied.query || applied.category || applied.start || applied.end
  );

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ArchiveSkeleton />
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
          <View style={styles.hero}>
            <Text style={styles.kicker}>The publication record</Text>
            <Text style={styles.title}>Archive</Text>
            <Text style={styles.description}>
              Revisit stories, campus moments, and student voices from previous publication periods of The Equalizer.
            </Text>
            <Text style={styles.count}>
              {data?.count ?? 0} archived {(data?.count ?? 0) === 1 ? "article" : "articles"}
            </Text>
          </View>

          <View style={styles.filterPanel}>
            <Text style={styles.filterKicker}>Find a story</Text>
            <Text style={styles.filterTitle}>Search the publication record</Text>

            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="Search archived stories"
              placeholderTextColor={colors.muted}
              returnKeyType="search"
              onSubmitEditing={applyFilters}
              style={styles.searchInput}
            />

            <Text style={styles.filterLabel}>Category</Text>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.categoryChips}
            >
              <FilterChip
                label="All"
                active={!selectedCategory}
                onPress={() => setSelectedCategory("")}
              />
              {(categories?.categories ?? []).map((category) => (
                <FilterChip
                  key={category.id}
                  label={category.name}
                  active={selectedCategory === category.slug}
                  onPress={() => setSelectedCategory(category.slug)}
                />
              ))}
            </ScrollView>

            <View style={styles.dateRow}>
              <View style={styles.dateField}>
                <Text style={styles.filterLabel}>From</Text>
                <TextInput
                  value={startDate}
                  onChangeText={setStartDate}
                  placeholder="YYYY-MM-DD"
                  placeholderTextColor="#8a9690"
                  keyboardType="numbers-and-punctuation"
                  maxLength={10}
                  style={styles.dateInput}
                />
              </View>
              <View style={styles.dateField}>
                <Text style={styles.filterLabel}>To</Text>
                <TextInput
                  value={endDate}
                  onChangeText={setEndDate}
                  placeholder="YYYY-MM-DD"
                  placeholderTextColor="#8a9690"
                  keyboardType="numbers-and-punctuation"
                  maxLength={10}
                  style={styles.dateInput}
                />
              </View>
            </View>

            {data?.filters.filter_error ? (
              <Text style={styles.filterError}>{data.filters.filter_error}</Text>
            ) : null}

            <View style={styles.actions}>
              <Pressable style={styles.applyButton} onPress={applyFilters}>
                <Text style={styles.applyButtonText}>Apply filters</Text>
              </Pressable>
              {filterActive ? (
                <Pressable style={styles.clearButton} onPress={clearFilters}>
                  <Text style={styles.clearButtonText}>Clear</Text>
                </Pressable>
              ) : null}
            </View>
          </View>

          {error ? <Text style={styles.inlineError}>{error}</Text> : null}

          {grouped.length > 0 ? (
            <View style={styles.results}>
              {grouped.map((group) => (
                <View key={group.label} style={styles.monthGroup}>
                  <View style={styles.monthHeading}>
                    <View style={styles.monthLine} />
                    <View>
                      <Text style={styles.monthKicker}>Publication month</Text>
                      <Text style={styles.monthTitle}>{group.label}</Text>
                    </View>
                  </View>

                  <View style={styles.cards}>
                    {group.articles.map((article) => (
                      <ArticleCard key={article.id} article={article} />
                    ))}
                  </View>
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyTitle}>No matching archived stories</Text>
              <Text style={styles.emptyText}>
                Try another keyword, category, or publication date range.
              </Text>
            </View>
          )}
        </ScrollView>
      )}
    </View>
  );
}

function FilterChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      style={[styles.chip, active && styles.chipActive]}
      onPress={onPress}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.white },
  scroll: { flex: 1, backgroundColor: colors.white },
  content: { paddingHorizontal: 14, paddingTop: 26, paddingBottom: 56 },
  hero: {
    paddingBottom: 20,
    borderBottomWidth: 3,
    borderBottomColor: colors.green,
  },
  kicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "900",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: {
    marginTop: 4,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 42,
    lineHeight: 45,
    fontWeight: "700",
  },
  description: { marginTop: 9, color: colors.muted, fontSize: 14, lineHeight: 22 },
  count: { marginTop: 11, color: colors.green, fontSize: 12, fontWeight: "800" },
  filterPanel: {
    marginTop: 18,
    padding: 15,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
    backgroundColor: colors.soft,
  },
  filterKicker: {
    color: colors.gold,
    fontSize: 10,
    fontWeight: "900",
    letterSpacing: 1.05,
    textTransform: "uppercase",
  },
  filterTitle: {
    marginTop: 4,
    marginBottom: 13,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 21,
    fontWeight: "700",
  },
  searchInput: {
    minHeight: 44,
    paddingHorizontal: 13,
    borderWidth: 1,
    borderColor: "#b9ccc3",
    borderRadius: 10,
    backgroundColor: colors.white,
    color: colors.greenDeep,
  },
  filterLabel: {
    marginTop: 11,
    color: colors.greenDeep,
    fontSize: 11.5,
    fontWeight: "800",
  },
  categoryChips: { gap: 7, paddingTop: 7, paddingRight: 8 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 999,
    backgroundColor: colors.white,
  },
  chipActive: { borderColor: colors.green, backgroundColor: colors.green },
  chipText: { color: colors.green, fontSize: 11.5, fontWeight: "700" },
  chipTextActive: { color: colors.white },
  dateRow: { flexDirection: "row", gap: 10, marginTop: 2 },
  dateField: { flex: 1 },
  dateInput: {
    minHeight: 43,
    marginTop: 5,
    paddingHorizontal: 11,
    borderWidth: 1,
    borderColor: "#c8d5cf",
    borderRadius: 9,
    backgroundColor: colors.white,
    color: colors.greenDeep,
    fontSize: 12.5,
  },
  filterError: { marginTop: 10, color: "#b42318", fontSize: 12, lineHeight: 17 },
  actions: { flexDirection: "row", gap: 8, marginTop: 13 },
  applyButton: {
    minHeight: 41,
    justifyContent: "center",
    paddingHorizontal: 16,
    borderRadius: 999,
    backgroundColor: colors.green,
  },
  applyButtonText: { color: colors.white, fontSize: 12.5, fontWeight: "800" },
  clearButton: {
    minHeight: 41,
    justifyContent: "center",
    paddingHorizontal: 16,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 999,
    backgroundColor: colors.white,
  },
  clearButtonText: { color: colors.greenDeep, fontSize: 12.5, fontWeight: "800" },
  inlineError: { marginTop: 14, color: "#b42318", fontSize: 12.5, lineHeight: 18 },
  results: { marginTop: 28, gap: 30 },
  monthGroup: { gap: 14 },
  monthHeading: { flexDirection: "row", alignItems: "center", gap: 12 },
  monthLine: { width: 34, height: 2, backgroundColor: colors.gold },
  monthKicker: {
    color: colors.gold,
    fontSize: 9.5,
    fontWeight: "900",
    letterSpacing: 1,
    textTransform: "uppercase",
  },
  monthTitle: {
    marginTop: 2,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 24,
    fontWeight: "700",
  },
  cards: { gap: 15 },
  emptyState: {
    marginTop: 28,
    padding: 30,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 14,
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
  emptyText: { marginTop: 8, color: colors.muted, lineHeight: 20, textAlign: "center" },
});
