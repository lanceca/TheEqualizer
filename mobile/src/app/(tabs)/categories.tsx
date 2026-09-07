import { useCallback, useEffect, useState } from "react";
import { RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { apiGet, Category } from "../../lib/api";

type Response = { categories: Category[] };

export default function CategoriesScreen() {
  const [items, setItems] = useState<Category[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("Loading categories…");

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    try {
      const data = await apiGet<Response>("/categories/");
      setItems(data.categories);
      setMessage("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load categories.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />}
    >
      <Text style={styles.heading}>Browse categories</Text>
      <Text style={styles.intro}>All public sections from The Equalizer.</Text>

      {message ? <Text style={styles.message}>{message}</Text> : null}

      <View style={styles.list}>
        {items.map((category) => (
          <View key={category.id} style={styles.card}>
            <Text style={styles.title}>{category.name}</Text>
            {category.description ? <Text style={styles.description}>{category.description}</Text> : null}
            <Text style={styles.count}>
              {category.article_count} published {category.article_count === 1 ? "article" : "articles"}
            </Text>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F7F4EC" },
  content: { padding: 18, paddingBottom: 36, gap: 8 },
  heading: { color: "#0E2A22", fontWeight: "900", fontSize: 28 },
  intro: { color: "#65736D", marginBottom: 10 },
  message: { color: "#65736D", paddingVertical: 20, textAlign: "center" },
  list: { gap: 12 },
  card: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D7DFDB", borderRadius: 15, padding: 16, gap: 6 },
  title: { color: "#173F32", fontWeight: "900", fontSize: 20 },
  description: { color: "#65736D", lineHeight: 19 },
  count: { color: "#C9A227", fontWeight: "800", fontSize: 12 },
});
