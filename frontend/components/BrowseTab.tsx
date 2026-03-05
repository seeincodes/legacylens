"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Routine {
  id: string;
  routine_type: string | null;
  file_path: string | null;
}

const TYPE_COLORS: Record<string, { color: string; bg: string }> = {
  driver: { color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
  computational: { color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
  blas: { color: "var(--chalk-amber)", bg: "var(--chalk-amber-light)" },
};

const ACTIONS = [
  { action: "explain", label: "Explain", color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
];

export default function BrowseTab() {
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/graph`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => setRoutines(data.nodes || []))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let list = routines;
    if (typeFilter) list = list.filter((r) => r.routine_type === typeFilter);
    if (search.trim()) {
      const q = search.trim().toUpperCase();
      list = list.filter((r) => r.id.includes(q));
    }
    return list.sort((a, b) => a.id.localeCompare(b.id));
  }, [routines, search, typeFilter]);

  const grouped = useMemo(() => {
    const groups: Record<string, Routine[]> = {};
    for (const r of filtered) {
      const letter = r.id[0] || "#";
      (groups[letter] ??= []).push(r);
    }
    return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
  }, [filtered]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center py-12">
        <div className="text-sm" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}>
          Loading routines...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center py-12">
        <p className="text-sm" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--chalk-pink)" }}>
          {error}
        </p>
      </div>
    );
  }

  return (
    <div className="w-full flex flex-col items-center px-4">
      <div className="w-full max-w-3xl flex flex-col gap-4">
        {/* Filter bar */}
        <div className="flex gap-3 items-center">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Filter routines..."
            className="flex-1 px-3 py-2 rounded-lg text-sm border"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              borderColor: "var(--paper-grid)",
              background: "var(--paper)",
              color: "var(--ink)",
            }}
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-lg px-3 py-2 text-sm border"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              borderColor: "var(--paper-grid)",
              background: "var(--paper)",
              color: "var(--ink)",
            }}
          >
            <option value="">All types</option>
            <option value="driver">Driver</option>
            <option value="computational">Computational</option>
            <option value="blas">BLAS</option>
          </select>
        </div>

        <div className="text-xs" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-faint)" }}>
          {filtered.length} routines
        </div>

        {/* Alphabetical groups */}
        {grouped.map(([letter, items]) => (
          <div key={letter}>
            <h3
              className="text-lg font-bold mb-2 mt-4"
              style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}
            >
              {letter}
            </h3>
            <div className="grid gap-1">
              {items.map((r) => {
                const tc = TYPE_COLORS[r.routine_type || ""];
                return (
                  <div
                    key={r.id}
                    className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-[var(--paper-dark)] transition-colors"
                  >
                    <Link
                      href={`/?q=${encodeURIComponent(r.id)}`}
                      className="text-sm font-medium shrink-0 hover:underline"
                      style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--chalk-blue)" }}
                    >
                      {r.id}
                    </Link>
                    {r.routine_type && (
                      <span
                        className="math-tag shrink-0"
                        style={{
                          color: tc?.color || "var(--ink-faint)",
                          background: tc?.bg || "var(--paper-dark)",
                        }}
                      >
                        {r.routine_type}
                      </span>
                    )}
                    {r.file_path && (
                      <span
                        className="text-xs truncate max-w-[180px]"
                        style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}
                      >
                        {r.file_path}
                      </span>
                    )}
                    <div className="ml-auto flex gap-1.5 shrink-0">
                      {ACTIONS.map((a) => (
                        <Link
                          key={a.action}
                          href={`/?routine=${encodeURIComponent(r.id)}&action=${a.action}`}
                          className="px-2 py-0.5 rounded text-[10px] font-medium hover:opacity-80 transition-opacity"
                          style={{
                            fontFamily: "var(--font-architects-daughter)",
                            color: a.color,
                            background: a.bg,
                            border: `1px solid ${a.color}`,
                          }}
                        >
                          {a.label}
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
