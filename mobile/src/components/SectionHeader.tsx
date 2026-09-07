import { StyleSheet, Text, View } from "react-native";

import { colors } from "../theme/colors";

type Props = {
  eyebrow?: string;
  title: string;
};

export function SectionHeader({ eyebrow, title }: Props) {
  return (
    <View style={styles.wrap}>
      {eyebrow ? <Text style={styles.eyebrow}>{eyebrow}</Text> : null}
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    gap: 3,
  },
  eyebrow: {
    color: colors.gold,
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 1.1,
    textTransform: "uppercase",
  },
  title: {
    color: colors.forestDark,
    fontSize: 24,
    fontWeight: "800",
  },
});
