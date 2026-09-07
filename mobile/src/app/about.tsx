import { useCallback, useEffect, useState } from "react";
import {
  Image,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { ScreenState } from "../components/ScreenState";
import { SiteHeader } from "../components/SiteHeader";
import { apiGet } from "../lib/api";
import type { AboutResponse } from "../lib/types";
import { colors, typography } from "../theme";

export default function AboutScreen() {
  const [data, setData] = useState<AboutResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (refresh = false) => {
    refresh ? setRefreshing(true) : setLoading(true);
    setError("");

    try {
      setData(await apiGet<AboutResponse>("/about-us/"));
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load About Us."
      );
    } finally {
      refresh ? setRefreshing(false) : setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const about = data?.about;

  return (
    <View style={styles.root}>
      <SiteHeader />

      {loading && !data ? (
        <ScreenState loading message="Loading About Us…" />
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
          {!about ? (
            <View style={styles.unavailable}>
              <Text style={styles.unavailableTitle}>
                About The Equalizer
              </Text>
              <Text style={styles.unavailableText}>
                This page is currently being prepared by the publication team.
              </Text>
            </View>
          ) : (
            <>
              <View style={styles.header}>
                <Text style={styles.kicker}>The Equalizer</Text>
                <Text style={styles.title}>{about.title}</Text>

                {about.subtitle ? (
                  <Text style={styles.subtitle}>{about.subtitle}</Text>
                ) : null}
              </View>

              {about.hero_image_url ? (
                <Image
                  source={{ uri: about.hero_image_url }}
                  style={styles.hero}
                  resizeMode="cover"
                />
              ) : null}

              <View style={styles.mainColumn}>
                <AboutSection
                  title="About The Equalizer"
                  body={about.overview}
                />
                <AboutSection
                  title="Our History"
                  body={about.history}
                />
              </View>

              {about.mission || about.vision ? (
                <View style={styles.sideColumn}>
                  {about.mission ? (
                    <AboutSideCard
                      title="Mission"
                      body={about.mission}
                    />
                  ) : null}

                  {about.vision ? (
                    <AboutSideCard
                      title="Vision"
                      body={about.vision}
                    />
                  ) : null}
                </View>
              ) : null}
            </>
          )}
        </ScrollView>
      )}
    </View>
  );
}

function AboutSection({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <Text style={styles.richCopy}>{body}</Text>
    </View>
  );
}

function AboutSideCard({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.sideCard}>
      <Text style={styles.sideCardTitle}>{title}</Text>
      <Text style={styles.richCopy}>{body}</Text>
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
    paddingBottom: 18,
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
  title: {
    marginTop: 4,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 40,
    lineHeight: 44,
    fontWeight: "700",
  },
  subtitle: {
    marginTop: 10,
    color: colors.muted,
    fontFamily: typography.serif,
    fontSize: 18,
    lineHeight: 26,
  },
  hero: {
    width: "100%",
    aspectRatio: 16 / 8.8,
    marginTop: 22,
    borderRadius: 12,
    backgroundColor: colors.soft,
  },
  mainColumn: {
    marginTop: 24,
    gap: 22,
  },
  section: {
    paddingBottom: 22,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  sectionTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 28,
    fontWeight: "700",
  },
  richCopy: {
    marginTop: 10,
    color: colors.ink,
    fontSize: 15,
    lineHeight: 25,
  },
  sideColumn: {
    marginTop: 24,
    gap: 14,
  },
  sideCard: {
    padding: 18,
    borderWidth: 1,
    borderTopWidth: 4,
    borderColor: colors.line,
    borderTopColor: colors.gold,
    borderRadius: 12,
    backgroundColor: colors.soft,
  },
  sideCardTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 24,
    fontWeight: "700",
  },
  unavailable: {
    marginTop: 20,
    paddingHorizontal: 20,
    paddingVertical: 48,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: 12,
    backgroundColor: colors.soft,
    alignItems: "center",
  },
  unavailableTitle: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 30,
    fontWeight: "700",
  },
  unavailableText: {
    marginTop: 8,
    color: colors.muted,
    textAlign: "center",
  },
});
