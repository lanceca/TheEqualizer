import { Platform } from "react-native";

export const colors = {
  green: "#173f32",
  greenDeep: "#0e2a22",
  gold: "#c9a227",
  ink: "#17231f",
  muted: "#66736d",
  line: "#dce4df",
  soft: "#f4f7f5",
  white: "#ffffff",
  headerGreen: "#184536",
  headerGreenDeep: "#0f2d24",
  headerGold: "#d6ad32",
};

export const typography = {
  serif: Platform.select({
    ios: "Georgia",
    android: "serif",
    default: "serif",
  }),
  sans: Platform.select({
    ios: "Arial",
    android: "sans-serif",
    default: "sans-serif",
  }),
};
