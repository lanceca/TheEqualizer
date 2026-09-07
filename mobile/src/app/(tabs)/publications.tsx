import { useCallback, useEffect, useState } from "react";
import { Image, Linking, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { apiGet, DigitalPublication, formatDate } from "../../lib/api";

type Response = { digital_publications: DigitalPublication[] };
type DetailResponse = { digital_publication: DigitalPublication };

export default function PublicationsScreen() {
  const [items, setItems] = useState<DigitalPublication[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("Loading publications…");

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    try {
      const data = await apiGet<Response>("/digital-publications/");
      setItems(data.digital_publications);
      setMessage("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load publications.");
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const openPdf = async (slug: string) => {
    try {
      const data = await apiGet<DetailResponse>(`/digital-publications/${encodeURIComponent(slug)}/`);
      if (data.digital_publication.pdf_url) {
        await Linking.openURL(data.digital_publication.pdf_url);
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to open publication.");
    }
  };

  return (
    <ScrollView
      style={styles.screen}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />}
    >
      <Text style={styles.heading}>Digital Publications</Text>
      <Text style={styles.intro}>Tap an issue to open its PDF edition.</Text>
      {message ? <Text style={styles.message}>{message}</Text> : null}

      <View style={styles.list}>
        {items.map((item) => (
          <Pressable key={item.id} style={styles.card} onPress={() => openPdf(item.slug)}>
            {item.cover_image_url ? <Image source={{ uri: item.cover_image_url }} style={styles.cover} /> : null}
            <View style={styles.info}>
              <Text style={styles.title}>{item.title}</Text>
              <Text style={styles.meta}>
                {item.volume || "Publication"}{item.issue_number ? ` • Issue ${item.issue_number}` : ""}
              </Text>
              <Text style={styles.meta}>{formatDate(item.publication_date)}</Text>
              {item.description ? <Text style={styles.description} numberOfLines={4}>{item.description}</Text> : null}
            </View>
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
  intro: { color: "#65736D", marginBottom: 10 },
  message: { color: "#65736D", paddingVertical: 16, textAlign: "center" },
  list: { gap: 12 },
  card: { flexDirection: "row", gap: 12, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D7DFDB", borderRadius: 15, padding: 12 },
  cover: { width: 96, height: 132, borderRadius: 8, backgroundColor: "#EAF0ED" },
  info: { flex: 1, justifyContent: "center", gap: 5 },
  title: { color: "#0E2A22", fontWeight: "900", fontSize: 18 },
  meta: { color: "#C9A227", fontSize: 12, fontWeight: "700" },
  description: { color: "#65736D", lineHeight: 18, fontSize: 13 },
});
