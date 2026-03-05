"use client";

import { Suspense, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import TabBar, { type TabId } from "@/components/TabBar";
import SearchTab from "@/components/SearchTab";
import MapTab from "@/components/MapTab";
import StatsTab from "@/components/StatsTab";
import BrowseTab from "@/components/BrowseTab";

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = (searchParams.get("tab") as TabId) || "search";
  const linkedRoutine = searchParams.get("routine");
  const linkedAction = searchParams.get("action");
  const initialQuery = searchParams.get("q");

  const setActiveTab = useCallback((tab: TabId) => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete("routine");
    params.delete("action");
    if (tab === "search") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    const qs = params.toString();
    router.push(qs ? `/?${qs}` : "/", { scroll: false });
  }, [searchParams, router]);

  return (
    <main className="relative z-10 min-h-screen flex flex-col">
      {/* Header */}
      <div className="text-center pt-8 pb-2">
        <h1
          className="text-5xl md:text-6xl"
          style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
        >
          LegacyLens
        </h1>
        <p
          className="mt-2 text-base"
          style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)", fontStyle: "italic" }}
        >
          Explore the LAPACK Fortran codebase with natural language
        </p>
      </div>

      {/* Tabs */}
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Tab Panels — all mounted, CSS visibility toggle */}
      <div className="flex-1 flex flex-col min-h-0" style={{ display: activeTab === "search" ? undefined : "none" }}>
        <SearchTab linkedRoutine={linkedRoutine} linkedAction={linkedAction} initialQuery={initialQuery || (linkedRoutine ? `What does ${linkedRoutine} do?` : null)} />
      </div>
      <div className="flex-1 flex flex-col min-h-0" style={{ display: activeTab === "map" ? undefined : "none" }}>
        <MapTab />
      </div>
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto" style={{ display: activeTab === "stats" ? undefined : "none" }}>
        <StatsTab />
      </div>
      <div className="flex-1 flex flex-col min-h-0 overflow-y-auto" style={{ display: activeTab === "browse" ? undefined : "none" }}>
        <BrowseTab />
      </div>

      {/* Footer — hidden on map tab to maximize graph space */}
      {activeTab !== "map" && (
        <footer
          className="mt-auto pt-10 pb-4 text-center text-xs"
          style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-faint)" }}
        >
          LAPACK — Linear Algebra PACKage — Univ. of Tennessee, UC Berkeley, NAG Ltd.
        </footer>
      )}
    </main>
  );
}

export default function Home() {
  return (
    <Suspense>
      <HomeContent />
    </Suspense>
  );
}
