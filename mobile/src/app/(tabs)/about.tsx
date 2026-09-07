import { useCallback, useEffect, useState } from "react";
import { Image, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { AboutPage, apiGet } from "../../lib/api";

type Response = { about: AboutPage | null };

export default function AboutScreen() {
  const [about, setAbout] = useState<AboutPage | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("Loading About Us…");

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    try {
      const data = await apiGet<Response>("/about-us/");
      setAbout(data.about);
      setMessage(data.about ? "" : "The About Us page has not been published yet.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load About Us.");
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
      {message ? <Text style={styles.message}>{message}</Text> : null}
      {about ? (
        <>
          {about.hero_image_url ? <Image source={{ uri: about.hero_image_url }} style={styles.hero} /> : null}
          <Text style={styles.title}>{about.title}</Text>
          {about.subtitle ? <Text style={styles.subtitle}>{about.subtitle}</Text> : null}
          <Section title="Overview" body={about.overview} />
          <Section title="History" body={about.history} />
          <Section title="Mission" body={about.mission} />
          <Section title="Vision" body={about.vision} />
        </>
      ) : null}
    </ScrollView>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  if (!body) return null;
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F7F4EC" },
  content: { padding: 18, paddingBottom: 36, gap: 14 },
  message: { color: "#65736D", textAlign: "center", paddingVertical: 20 },
  hero: { width: "100%", height: 220, borderRadius: 17, backgroundColor: "#EAF0ED" },
  title: { color: "#0E2A22", fontWeight: "900", fontSize: 30 },
  subtitle: { color: "#C9A227", fontSize: 16, lineHeight: 22, fontWeight: "700" },
  section: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D7DFDB", borderRadius: 14, padding: 16, gap: 7 },
  sectionTitle: { color: "#173F32", fontWeight: "900", fontSize: 18 },
  body: { color: "#1D2924", lineHeight: 22, fontSize: 14 },
});
