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
import {
  apiGet,
  Article,
  DigitalPublication,
  SchoolUpdate,
  formatDate,
} from "../../lib/api";

type HomeResponse = {
  latest_articles: Article[];
  school_updates: SchoolUpdate[];
  digital_publications: DigitalPublication[];
};

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
      setError(err instanceof Error ? err.message : "Unable to load The Equalizer.");
    } finally {
      refresh ? setRefreshing(false) : setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return <CenteredMessage text="Loading The Equalizer…" />;
  }

  if (error && !data) {
    return <CenteredMessage text={`${error}\n\nPull down or reopen the app to try again.`} />;
  }

  const articles = data?.latest_articles ?? [];
  const updates = data?.school_updates ?? [];
  const publications = data?.digital_publications ?? [];

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => load(true)}
          tintColor="#173F32"
        />
      }
    >
      <View style={styles.heroBox}>
        <Text style={styles.eyebrow}>STUDENT PUBLICATION</Text>
        <Text style={styles.brand}>THE EQUALIZER</Text>
        <Text style={styles.heroCopy}>
          Stories, perspectives, and campus updates refreshed directly from the publication website.
        </Text>
      </View>

      <SectionTitle eyebrow="Latest" title="Top stories" />

      {articles.length === 0 ? (
        <Text style={styles.empty}>No published articles yet.</Text>
      ) : (
        articles.slice(0, 6).map((article, index) => (
          <Pressable
            key={article.id}
            style={styles.articleCard}
            onPress={() =>
              router.push({
                pathname: "/article/[slug]",
                params: { slug: article.slug },
              })
            }
          >
            {article.hero_image_url ? (
              <Image
                source={{ uri: article.hero_image_url }}
                style={[styles.articleImage, index > 0 && styles.articleImageSmall]}
              />
            ) : null}
            <View style={styles.cardBody}>
              <Text style={styles.category}>{article.category.name}</Text>
              <Text style={styles.articleTitle}>{article.title}</Text>
              {article.excerpt ? (
                <Text style={styles.excerpt} numberOfLines={3}>
                  {article.excerpt}
                </Text>
              ) : null}
              <Text style={styles.meta}>
                {article.author.display_name} • {formatDate(article.published_at)}
              </Text>
            </View>
          </Pressable>
        ))
      )}

      <SectionTitle eyebrow="Campus" title="School updates" />

      {updates.length === 0 ? (
        <Text style={styles.empty}>No active school updates.</Text>
      ) : (
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View style={styles.horizontalRow}>
            {updates.map((update) => (
              <View key={update.id} style={styles.updateCard}>
                {update.image_url ? (
                  <Image source={{ uri: update.image_url }} style={styles.updateImage} />
                ) : null}
                <Text style={styles.updateTitle}>{update.title}</Text>
                <Text style={styles.excerpt} numberOfLines={3}>
                  {update.summary}
                </Text>
              </View>
            ))}
          </View>
        </ScrollView>
      )}

      <SectionTitle eyebrow="Archive" title="Digital publications" />

      {publications.length === 0 ? (
        <Text style={styles.empty}>No digital publications yet.</Text>
      ) : (
        publications.map((publication) => (
          <View key={publication.id} style={styles.publicationRow}>
            {publication.cover_image_url ? (
              <Image
                source={{ uri: publication.cover_image_url }}
                style={styles.cover}
              />
            ) : null}
            <View style={{ flex: 1 }}>
              <Text style={styles.articleTitle}>{publication.title}</Text>
              <Text style={styles.meta}>
                {publication.volume || "Publication"}
                {publication.issue_number ? ` • Issue ${publication.issue_number}` : ""}
              </Text>
            </View>
          </View>
        ))
      )}
    </ScrollView>
  );
}

function SectionTitle({ eyebrow, title }: { eyebrow: string; title: string }) {
  return (
    <View style={{ gap: 2 }}>
      <Text style={styles.eyebrowDark}>{eyebrow}</Text>
      <Text style={styles.sectionTitle}>{title}</Text>
    </View>
  );
}

function CenteredMessage({ text }: { text: string }) {
  return (
    <View style={styles.centered}>
      <Text style={styles.centeredText}>{text}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F7F4EC" },
  content: { padding: 18, paddingBottom: 36, gap: 18 },
  heroBox: { backgroundColor: "#0E2A22", borderRadius: 20, padding: 22, gap: 7 },
  eyebrow: { color: "#C9A227", fontWeight: "900", fontSize: 11, letterSpacing: 1.2 },
  eyebrowDark: { color: "#C9A227", fontWeight: "900", fontSize: 11, letterSpacing: 1 },
  brand: { color: "#FFFFFF", fontWeight: "900", fontSize: 30 },
  heroCopy: { color: "#E6ECE9", lineHeight: 20 },
  sectionTitle: { color: "#0E2A22", fontWeight: "900", fontSize: 24 },
  articleCard: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D7DFDB", borderRadius: 16, overflow: "hidden" },
  articleImage: { width: "100%", height: 200, backgroundColor: "#EAF0ED" },
  articleImageSmall: { height: 150 },
  cardBody: { padding: 15, gap: 6 },
  category: { color: "#C9A227", fontWeight: "900", fontSize: 11, textTransform: "uppercase" },
  articleTitle: { color: "#0E2A22", fontWeight: "900", fontSize: 19, lineHeight: 23 },
  excerpt: { color: "#65736D", lineHeight: 19, fontSize: 13 },
  meta: { color: "#65736D", fontSize: 12, marginTop: 3 },
  horizontalRow: { flexDirection: "row", gap: 12, paddingRight: 18 },
  updateCard: { width: 270, backgroundColor: "#FFFFFF", borderRadius: 15, borderWidth: 1, borderColor: "#D7DFDB", padding: 12, gap: 7 },
  updateImage: { width: "100%", height: 135, borderRadius: 10, backgroundColor: "#EAF0ED" },
  updateTitle: { color: "#0E2A22", fontWeight: "900", fontSize: 17 },
  publicationRow: { flexDirection: "row", gap: 12, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D7DFDB", borderRadius: 14, padding: 12, alignItems: "center" },
  cover: { width: 68, height: 92, borderRadius: 7, backgroundColor: "#EAF0ED" },
  empty: { color: "#65736D", fontStyle: "italic" },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24, backgroundColor: "#F7F4EC" },
  centeredText: { color: "#65736D", textAlign: "center", lineHeight: 21 },
});
