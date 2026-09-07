import { useCallback, useEffect, useState } from "react";
import { Image, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { apiGet, PeopleGroup } from "../../lib/api";

type Response = { groups: PeopleGroup[] };

export default function PeopleScreen() {
  const [groups, setGroups] = useState<PeopleGroup[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [message, setMessage] = useState("Loading people & teams…");

  const load = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    try {
      const data = await apiGet<Response>("/people/");
      setGroups(data.groups);
      setMessage("");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Unable to load people.");
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
      <Text style={styles.heading}>People & Teams</Text>
      <Text style={styles.intro}>Meet the people connected to The Equalizer.</Text>
      {message ? <Text style={styles.message}>{message}</Text> : null}

      {groups.map((group) => (
        <View key={group.slug} style={styles.group}>
          <Text style={styles.groupTitle}>{group.title}</Text>
          {group.profiles.map((profile) => (
            <View key={profile.id} style={styles.card}>
              {profile.image_url ? (
                <Image source={{ uri: profile.image_url }} style={styles.avatar} />
              ) : (
                <View style={styles.avatar} />
              )}
              <View style={styles.info}>
                <Text style={styles.name}>{profile.name}</Text>
                {profile.role_title ? <Text style={styles.role}>{profile.role_title}</Text> : null}
                {profile.school_position ? <Text style={styles.detail}>{profile.school_position}</Text> : null}
                {profile.institute_department ? <Text style={styles.detail}>{profile.institute_department}</Text> : null}
              </View>
            </View>
          ))}
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#F7F4EC" },
  content: { padding: 18, paddingBottom: 36, gap: 16 },
  heading: { color: "#0E2A22", fontWeight: "900", fontSize: 28 },
  intro: { color: "#65736D", marginTop: -8 },
  message: { color: "#65736D", textAlign: "center", paddingVertical: 20 },
  group: { gap: 9 },
  groupTitle: { color: "#C9A227", fontWeight: "900", fontSize: 18 },
  card: { flexDirection: "row", gap: 12, backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#D7DFDB", borderRadius: 14, padding: 11 },
  avatar: { width: 70, height: 70, borderRadius: 35, backgroundColor: "#EAF0ED" },
  info: { flex: 1, justifyContent: "center", gap: 3 },
  name: { color: "#0E2A22", fontWeight: "900", fontSize: 17 },
  role: { color: "#C9A227", fontWeight: "700", fontSize: 13 },
  detail: { color: "#65736D", fontSize: 12 },
});
