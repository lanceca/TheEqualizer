import { Tabs } from "expo-router";
import { Text } from "react-native";

function Icon({ label, focused }: { label: string; focused: boolean }) {
  return <Text style={{ fontSize: 16, opacity: focused ? 1 : 0.55 }}>{label}</Text>;
}

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerStyle: { backgroundColor: "#173F32" },
        headerTintColor: "#FFFFFF",
        headerTitleStyle: { fontWeight: "800" },
        tabBarActiveTintColor: "#173F32",
        tabBarInactiveTintColor: "#65736D",
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "Home",
          headerTitle: "The Equalizer",
          tabBarIcon: ({ focused }) => <Icon label="⌂" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="categories"
        options={{
          title: "Categories",
          tabBarIcon: ({ focused }) => <Icon label="▦" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="publications"
        options={{
          title: "Publications",
          tabBarIcon: ({ focused }) => <Icon label="▤" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="people"
        options={{
          title: "People",
          tabBarIcon: ({ focused }) => <Icon label="♟" focused={focused} />,
        }}
      />
      <Tabs.Screen
        name="about"
        options={{
          title: "About",
          tabBarIcon: ({ focused }) => <Icon label="ⓘ" focused={focused} />,
        }}
      />
    </Tabs>
  );
}
