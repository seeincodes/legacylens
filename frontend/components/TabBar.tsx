"use client";

const TABS = [
  { id: "search", label: "Search", color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
  { id: "map", label: "Map", color: "var(--chalk-purple)", bg: "var(--chalk-purple-light)" },
  { id: "stats", label: "Stats", color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
  { id: "browse", label: "Browse", color: "var(--chalk-amber)", bg: "var(--chalk-amber-light)" },
] as const;

export type TabId = (typeof TABS)[number]["id"];

interface TabBarProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

export default function TabBar({ activeTab, onTabChange }: TabBarProps) {
  return (
    <nav className="flex justify-center gap-2 mt-2 mb-4">
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className="px-4 py-2 rounded-2xl font-bold text-sm transition-all cursor-pointer"
            style={{
              fontFamily: "var(--font-architects-daughter)",
              color: tab.color,
              background: isActive ? tab.bg : "transparent",
              border: isActive ? `2px dashed ${tab.color}` : "2px dashed transparent",
              boxShadow: isActive ? `1px 1px 0 rgba(0,0,0,0.1)` : "none",
              opacity: isActive ? 1 : 0.6,
            }}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
