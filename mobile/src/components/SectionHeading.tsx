import { StyleSheet, Text, View } from "react-native";

import { colors, typography } from "../theme";

type Props = {
  kicker: string;
  title: string;
  countText?: string;
};

export function SectionHeading({ kicker, title, countText }: Props) {
  return (
    <View style={styles.wrapper}>
      <View style={styles.copy}>
        <Text style={styles.kicker}>{kicker}</Text>
        <Text style={styles.title}>{title}</Text>
      </View>

      {countText ? <Text style={styles.count}>{countText}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    gap: 7,
    paddingBottom: 12,
    marginBottom: 18,
    borderBottomWidth: 3,
    borderBottomColor: colors.green,
  },
  copy: {
    gap: 4,
  },
  kicker: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.3,
    textTransform: "uppercase",
  },
  title: {
    color: colors.greenDeep,
    fontFamily: typography.serif,
    fontSize: 34,
    fontWeight: "700",
    lineHeight: 38,
  },
  count: {
    color: colors.muted,
    fontSize: 12,
  },
});
