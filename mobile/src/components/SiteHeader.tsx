import { useState } from "react";
import {
  Image,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { LOGO_URL } from "../lib/api";
import { colors, typography } from "../theme";

const categories = [
  ["News", "news"],
  ["Editorials", "editorials"],
  ["Features", "features"],
  ["Cartoonings", "cartoonings"],
  ["Videos", "videos"],
  ["Special Showcase", "special-showcase"],
  ["Sports", "sports"],
  ["Campus Life", "campus-life"],
  ["Opinion", "opinion"],
] as const;

export function SiteHeader() {
  const insets = useSafeAreaInsets();
  const [categoryOpen, setCategoryOpen] = useState(false);

  const go = (pathname: string) => {
    router.push(pathname as never);
  };

  const goCategory = (name: string, slug: string) => {
    setCategoryOpen(false);
    router.push({
      pathname: "/category/[slug]",
      params: {
        slug,
        title: name,
      },
    });
  };

  return (
    <>
      <View style={[styles.siteHeader, { paddingTop: insets.top }]}>
        <Pressable style={styles.brand} onPress={() => go("/")}>
          <Image source={{ uri: LOGO_URL }} style={styles.logo} />

          <View style={styles.brandText}>
            <Text style={styles.brandTitle}>The Equalizer</Text>
            <Text style={styles.brandSubtitle} numberOfLines={2}>
              The Official Student Publication of Mabalacat City College
            </Text>
          </View>
        </Pressable>
      </View>

      <View style={styles.publicNavigation}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.navigationInner}
        >
          <NavButton label="Home" onPress={() => go("/")} />
          <NavButton
            label="Digital Publications"
            onPress={() => go("/digital-publications")}
          />
          <NavButton
            label="School Updates"
            onPress={() => go("/school-updates")}
          />
          <NavButton label="About Us" onPress={() => go("/about")} />
          <NavButton
            label="People & Teams"
            onPress={() => go("/people")}
          />

          <Pressable
            style={styles.categoryToggle}
            onPress={() => setCategoryOpen(true)}
          >
            <Text style={styles.categoryToggleText}>Article Categories</Text>
            <Text style={styles.categoryArrow}>▾</Text>
          </Pressable>
        </ScrollView>
      </View>

      <Modal
        visible={categoryOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setCategoryOpen(false)}
      >
        <Pressable
          style={styles.overlay}
          onPress={() => setCategoryOpen(false)}
        >
          <Pressable style={styles.categorySheet} onPress={() => {}}>
            <View style={styles.categorySheetHeader}>
              <View>
                <Text style={styles.categoryKicker}>The Equalizer</Text>
                <Text style={styles.categoryTitle}>Article Categories</Text>
              </View>

              <Pressable
                style={styles.closeButton}
                onPress={() => setCategoryOpen(false)}
              >
                <Text style={styles.closeText}>×</Text>
              </Pressable>
            </View>

            <View style={styles.categoryGrid}>
              {categories.map(([name, slug]) => (
                <Pressable
                  key={slug}
                  style={styles.categoryItem}
                  onPress={() => goCategory(name, slug)}
                >
                  <Text style={styles.categoryItemText}>{name}</Text>
                </Pressable>
              ))}
            </View>
          </Pressable>
        </Pressable>
      </Modal>
    </>
  );
}

function NavButton({
  label,
  onPress,
}: {
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable style={styles.navButton} onPress={onPress}>
      <Text style={styles.navButtonText}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  siteHeader: {
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: "#d5ddd8",
  },
  brand: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  logo: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 2,
    borderColor: colors.headerGold,
    backgroundColor: colors.white,
  },
  brandText: {
    flex: 1,
    minWidth: 0,
  },
  brandTitle: {
    color: colors.headerGreen,
    fontSize: 20,
    lineHeight: 22,
    fontWeight: "800",
  },
  brandSubtitle: {
    marginTop: 4,
    color: "#6f7a74",
    fontSize: 10.5,
    lineHeight: 14,
  },
  publicNavigation: {
    backgroundColor: colors.white,
    borderBottomWidth: 1,
    borderBottomColor: colors.line,
  },
  navigationInner: {
    gap: 7,
    paddingHorizontal: 10,
    paddingVertical: 9,
  },
  navButton: {
    minHeight: 38,
    justifyContent: "center",
    paddingHorizontal: 12,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "transparent",
    backgroundColor: colors.white,
  },
  navButtonText: {
    color: colors.green,
    fontSize: 12.5,
    fontWeight: "700",
  },
  categoryToggle: {
    minHeight: 38,
    flexDirection: "row",
    alignItems: "center",
    gap: 7,
    paddingHorizontal: 12,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#9fb9ad",
    backgroundColor: colors.soft,
  },
  categoryToggleText: {
    color: colors.greenDeep,
    fontSize: 12.5,
    fontWeight: "700",
  },
  categoryArrow: {
    color: colors.greenDeep,
    fontSize: 11,
  },
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(6, 14, 11, 0.55)",
  },
  categorySheet: {
    maxHeight: "78%",
    paddingHorizontal: 16,
    paddingTop: 18,
    paddingBottom: 28,
    borderTopLeftRadius: 22,
    borderTopRightRadius: 22,
    backgroundColor: colors.white,
  },
  categorySheetHeader: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: 12,
    marginBottom: 16,
  },
  categoryKicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  categoryTitle: {
    marginTop: 3,
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 28,
    fontWeight: "700",
  },
  closeButton: {
    width: 38,
    height: 38,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 19,
    backgroundColor: colors.soft,
  },
  closeText: {
    color: colors.greenDeep,
    fontSize: 26,
    lineHeight: 28,
  },
  categoryGrid: {
    gap: 7,
  },
  categoryItem: {
    minHeight: 44,
    justifyContent: "center",
    paddingHorizontal: 13,
    borderWidth: 1,
    borderColor: "transparent",
    borderRadius: 9,
    backgroundColor: "#f6f8f7",
  },
  categoryItemText: {
    color: colors.greenDeep,
    fontSize: 14,
    fontWeight: "700",
  },
});
