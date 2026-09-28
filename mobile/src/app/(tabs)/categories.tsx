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

import { CategorySkeleton } from "../../components/SkeletonLayouts";
import { apiGet } from "../../lib/api";
import type { Category } from "../../lib/types";

type Response = { categories: Category[] };

export default function CategoriesScreen() {
  const [items, setItems] = useState<Category[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("Loading categories…");

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(true);

    try {
      const data = await apiGet<Response>("/categories/");
      setItems(data.categories);
      setMessage("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load categories.");
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && items.length === 0) {
    return <CategorySkeleton />;
  }

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />
      }
    >
      <Text style={styles.heading}>Browse categories</Text>
      <Text style={styles.intro}>
        Open a category to search stories and filter them by publication date.
      </Text>

      <Pressable
        style={styles.archiveCard}
        onPress={() => router.push("/archive" as never)}
      >
        <Text style={styles.archiveKicker}>PUBLICATION RECORD</Text>
        <Text style={styles.archiveTitle}>Browse the Archive</Text>
        <Text style={styles.archiveCopy}>
          Revisit previously published stories grouped by their original publication period.
        </Text>
      </Pressable>

      {message ? <Text style={styles.message}>{message}</Text> : null}

      <View style={styles.list}>
        {items.map((category) => (
          <Pressable
            key={category.id}
            style={({ pressed }) => [styles.card, pressed && styles.cardPressed]}
            onPress={() =>
              router.push({
                pathname: "/category/[slug]",
                params: { slug: category.slug, title: category.name },
              })
            }
          >
            <Text style={styles.title}>{category.name}</Text>
            {category.description ? (
              <Text style={styles.description}>{category.description}</Text>
            ) : null}
            <Text style={styles.count}>
              {category.article_count} published {category.article_count === 1 ? "article" : "articles"}
            </Text>
            <Text style={styles.openLink}>Open category →</Text>
          </Pressable>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F7F4EC" },
  content: { padding: 18, paddingBottom: 36, gap: 8 },
  heading: { color: "#0E2A22", fontWeight: "900", fontSize: 28 },
  intro: { color: "#65736D", marginBottom: 10, lineHeight: 20 },
  archiveCard: {
    marginBottom: 8,
    padding: 17,
    borderRadius: 16,
    backgroundColor: "#173F32",
  },
  archiveKicker: { color: "#C9A227", fontSize: 10, fontWeight: "900", letterSpacing: 1.1 },
  archiveTitle: { marginTop: 4, color: "#FFFFFF", fontSize: 21, fontWeight: "900" },
  archiveCopy: { marginTop: 5, color: "#DCE6E1", fontSize: 12.5, lineHeight: 18 },
  message: { color: "#65736D", paddingVertical: 20, textAlign: "center" },
  list: { gap: 12 },
  card: {
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#D7DFDB",
    borderRadius: 15,
    padding: 16,
    gap: 6,
  },
  cardPressed: { opacity: 0.82 },
  title: { color: "#173F32", fontWeight: "900", fontSize: 20 },
  description: { color: "#65736D", lineHeight: 19 },
  count: { color: "#C9A227", fontWeight: "800", fontSize: 12 },
  openLink: { marginTop: 2, color: "#173F32", fontWeight: "800", fontSize: 12 },
});
