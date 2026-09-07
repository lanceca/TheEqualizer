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

import { ScreenState } from "../components/ScreenState";
import { SiteHeader } from "../components/SiteHeader";
import { apiGet } from "../lib/api";
import type { PeopleResponse } from "../lib/types";
import { colors, typography } from "../theme";

export default function PeopleScreen() {
  const [data, setData] = useState<PeopleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [openGroup, setOpenGroup] = useState<string | null>(null);

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");

    try {
      setData(await apiGet<PeopleResponse>("/people/"));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load People & Teams."
      );
    } finally {
      refresh ? setRefreshing(false) : setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const groups = data?.groups ?? [];

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ScreenState loading message="Loading People & Teams…" />
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
            <Text style={styles.kicker}>The Equalizer</Text>
            <Text style={styles.title}>People & Teams</Text>
            <Text style={styles.description}>
              Meet the people connected to The Equalizer, the project,
              and the academic community behind it.
            </Text>
          </View>

          <View style={styles.tiles}>
            {groups.map((group, index) => {
              const active = openGroup === group.slug;

              return (
                <View key={group.slug}>
                  <Pressable
                    style={[
                      styles.tile,
                      index === groups.length - 1 && styles.tileWide,
                      active && styles.tileActive,
                    ]}
                    onPress={() =>
                      setOpenGroup(active ? null : group.slug)
                    }
                  >
                    <Text style={styles.tileKicker}>
                      {active ? "Selected" : "Explore"}
                    </Text>
                    <Text style={styles.tileTitle}>{group.title}</Text>
                    <Text style={styles.tileCount}>
                      {group.profiles.length}{" "}
                      {group.profiles.length === 1 ? "profile" : "profiles"}
                    </Text>
                  </Pressable>

                  {active ? (
                    <View style={styles.profileList}>
                      {group.profiles.length > 0 ? (
                        group.profiles.map((profile) => (
                          <View key={profile.id} style={styles.profileCard}>
                            {profile.image_url ? (
                              <Image
                                source={{ uri: profile.image_url }}
                                style={styles.avatar}
                                resizeMode="cover"
                              />
                            ) : (
                              <View
                                style={[styles.avatar, styles.avatarPlaceholder]}
                              />
                            )}

                            <View style={styles.profileCopy}>
                              <Text style={styles.profileName}>
                                {profile.name}
                              </Text>

                              {profile.role_title ? (
                                <Text style={styles.profileRole}>
                                  {profile.role_title}
                                </Text>
                              ) : null}

                              {profile.school_position ? (
                                <Text style={styles.profileDetail}>
                                  {profile.school_position}
                                </Text>
                              ) : null}

                              {profile.institute_department ? (
                                <Text style={styles.profileDetail}>
                                  {profile.institute_department}
                                </Text>
                              ) : null}

                              {profile.courses_handled ? (
                                <Text style={styles.profileBody}>
                                  {profile.courses_handled}
                                </Text>
                              ) : null}

                              {profile.achievements ? (
                                <Text style={styles.profileBody}>
                                  {profile.achievements}
                                </Text>
                              ) : null}

                              {profile.additional_information ? (
                                <Text style={styles.profileBody}>
                                  {profile.additional_information}
                                </Text>
                              ) : null}
                            </View>
                          </View>
                        ))
                      ) : (
                        <Text style={styles.emptyText}>
                          No profiles in this section yet.
                        </Text>
                      )}
                    </View>
                  ) : null}
                </View>
              );
            })}
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
    paddingTop: 30,
    paddingBottom: 54,
  },
  header: {
    maxWidth: 820,
    alignItems: "center",
    marginBottom: 28,
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
    textAlign: "center",
  },
  description: {
    marginTop: 10,
    color: colors.muted,
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
  },
  tiles: {
    gap: 14,
  },
  tile: {
    minHeight: 170,
    justifyContent: "flex-end",
    padding: 20,
    borderWidth: 1,
    borderColor: "#cad8d1",
    borderRadius: 16,
    backgroundColor: "#f1f6f3",
  },
  tileWide: {
    minHeight: 160,
  },
  tileActive: {
    borderColor: colors.green,
    backgroundColor: "#edf4f0",
  },
  tileKicker: {
    marginBottom: "auto",
    color: colors.gold,
    fontSize: 10.5,
    fontWeight: "800",
    textTransform: "uppercase",
    letterSpacing: 1.2,
  },
  tileTitle: {
    marginTop: 24,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 29,
    fontWeight: "700",
  },
  tileCount: {
    marginTop: 6,
    color: colors.muted,
    fontSize: 12,
  },
  profileList: {
    marginTop: 10,
    gap: 10,
  },
  profileCard: {
    flexDirection: "row",
    gap: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 13,
    backgroundColor: colors.white,
  },
  avatar: {
    width: 82,
    height: 82,
    borderRadius: 8,
    backgroundColor: colors.soft,
  },
  avatarPlaceholder: {
    borderWidth: 1,
    borderColor: colors.line,
  },
  profileCopy: {
    flex: 1,
    minWidth: 0,
  },
  profileName: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 20,
    fontWeight: "700",
  },
  profileRole: {
    marginTop: 3,
    color: colors.gold,
    fontSize: 12.5,
    fontWeight: "800",
  },
  profileDetail: {
    marginTop: 3,
    color: colors.muted,
    fontSize: 11.5,
  },
  profileBody: {
    marginTop: 7,
    color: colors.ink,
    fontSize: 12.5,
    lineHeight: 19,
  },
  emptyText: {
    color: colors.muted,
    fontStyle: "italic",
    textAlign: "center",
    paddingVertical: 20,
  },
});
