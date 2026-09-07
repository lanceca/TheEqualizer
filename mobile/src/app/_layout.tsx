import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";

import { colors } from "../theme";

export default function RootLayout() {
  return (
    <>
      <StatusBar style="dark" backgroundColor={colors.white} />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: {
            backgroundColor: colors.white,
          },
          animation: "slide_from_right",
        }}
      />
    </>
  );
}
