"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Stats {
  total_routines: number;
  total_files: number;
  total_loc: number;
  by_routine_type: { routine_type: string; count: number }[];
  by_precision: { precision_type: string; count: number }[];
  largest_routines: { subroutine_name: string; file_path: string; lines: number }[];
  most_called: { subroutine_name: string; call_count: number }[];
}

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/stats`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then(setStats)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <div
          className="text-sm"
          style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
        >
          Loading stats…
        </div>
      </main>
    );
  }

  if (error || !stats) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center px-4">
        <p
          className="text-sm"
          style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--chalk-pink)" }}
        >
          {error || "Failed to load stats"}
        </p>
        <Link
          href="/"
          className="mt-4 text-sm underline"
          style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--chalk-blue)" }}
        >
          Back to search
        </Link>
      </main>
    );
  }

  const maxRoutineType = stats.by_routine_type.length ? Math.max(...stats.by_routine_type.map((r) => r.count), 1) : 1;
  const maxPrecision = stats.by_precision.length ? Math.max(...stats.by_precision.map((r) => r.count), 1) : 1;
  const maxLines = stats.largest_routines.length ? Math.max(...stats.largest_routines.map((r) => r.lines), 1) : 1;
  const maxCalls = stats.most_called.length ? Math.max(...stats.most_called.map((r) => r.call_count), 1) : 1;

  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-12">
      <div className="w-full max-w-2xl flex flex-col gap-8">
        <div className="flex items-center justify-between">
          <div className="flex gap-3">
            <Link
              href="/"
              className="text-sm"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--chalk-blue)",
              }}
            >
              ← Search
            </Link>
            <Link
              href="/map"
              className="text-sm"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--chalk-purple)",
              }}
            >
              Map
            </Link>
          </div>
          <div className="text-center">
            <h1
              className="text-3xl"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--ink)",
              }}
            >
              Codebase Stats
            </h1>
            <a
              href="https://github.com/Reference-LAPACK/lapack"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs mt-1 inline-block"
              style={{
                fontFamily: "var(--font-jetbrains-mono)",
                color: "var(--chalk-blue)",
              }}
            >
              View source on GitHub →
            </a>
          </div>
          <span className="w-14" />
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-3 gap-4">
          <div
            className="math-card p-4 text-center"
            style={{ fontFamily: "var(--font-crimson-pro)" }}
          >
            <div className="text-2xl font-bold" style={{ color: "var(--chalk-blue)" }}>
              {stats.total_routines.toLocaleString()}
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--ink-light)" }}>
              Routines
            </div>
          </div>
          <div
            className="math-card p-4 text-center"
            style={{ fontFamily: "var(--font-crimson-pro)" }}
          >
            <div className="text-2xl font-bold" style={{ color: "var(--chalk-purple)" }}>
              {stats.total_files.toLocaleString()}
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--ink-light)" }}>
              Files
            </div>
          </div>
          <div
            className="math-card p-4 text-center"
            style={{ fontFamily: "var(--font-crimson-pro)" }}
          >
            <div className="text-2xl font-bold" style={{ color: "var(--chalk-green)" }}>
              {stats.total_loc.toLocaleString()}
            </div>
            <div className="text-xs mt-1" style={{ color: "var(--ink-light)" }}>
              Lines
            </div>
          </div>
        </div>

        {/* By routine type */}
        <div className="math-card p-5">
          <h2
            className="text-sm font-bold mb-3"
            style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
          >
            By routine type
          </h2>
          <div className="space-y-2">
            {stats.by_routine_type.map((r) => (
              <div key={r.routine_type} className="flex items-center gap-3">
                <span
                  className="w-24 text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink)" }}
                >
                  {r.routine_type}
                </span>
                <div
                  className="flex-1 h-5 rounded overflow-hidden"
                  style={{ background: "var(--paper-dark)" }}
                >
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${(r.count / maxRoutineType) * 100}%`,
                      background: "var(--chalk-blue)",
                    }}
                  />
                </div>
                <span
                  className="w-10 text-right text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-light)" }}
                >
                  {r.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* By precision */}
        <div className="math-card p-5">
          <h2
            className="text-sm font-bold mb-3"
            style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
          >
            By precision
          </h2>
          <div className="space-y-2">
            {stats.by_precision.map((r) => (
              <div key={r.precision_type} className="flex items-center gap-3">
                <span
                  className="w-24 text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink)" }}
                >
                  {r.precision_type}
                </span>
                <div
                  className="flex-1 h-5 rounded overflow-hidden"
                  style={{ background: "var(--paper-dark)" }}
                >
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${(r.count / maxPrecision) * 100}%`,
                      background: "var(--chalk-purple)",
                    }}
                  />
                </div>
                <span
                  className="w-10 text-right text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-light)" }}
                >
                  {r.count}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Largest routines */}
        <div className="math-card p-5">
          <h2
            className="text-sm font-bold mb-3"
            style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
          >
            Top 10 largest routines
          </h2>
          <div className="space-y-2">
            {stats.largest_routines.map((r) => (
              <div key={r.subroutine_name} className="flex items-center gap-3">
                <span
                  className="w-20 text-xs font-medium"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink)" }}
                >
                  {r.subroutine_name}
                </span>
                <div
                  className="flex-1 h-4 rounded overflow-hidden"
                  style={{ background: "var(--paper-dark)" }}
                >
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${(r.lines / maxLines) * 100}%`,
                      background: "var(--chalk-green)",
                    }}
                  />
                </div>
                <span
                  className="w-12 text-right text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-light)" }}
                >
                  {r.lines}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Most called */}
        <div className="math-card p-5">
          <h2
            className="text-sm font-bold mb-3"
            style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
          >
            Top 10 most-called routines
          </h2>
          <div className="space-y-2">
            {stats.most_called.map((r) => (
              <div key={r.subroutine_name} className="flex items-center gap-3">
                <span
                  className="w-20 text-xs font-medium"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink)" }}
                >
                  {r.subroutine_name}
                </span>
                <div
                  className="flex-1 h-4 rounded overflow-hidden"
                  style={{ background: "var(--paper-dark)" }}
                >
                  <div
                    className="h-full rounded"
                    style={{
                      width: `${(r.call_count / maxCalls) * 100}%`,
                      background: "var(--chalk-amber)",
                    }}
                  />
                </div>
                <span
                  className="w-12 text-right text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-light)" }}
                >
                  {r.call_count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
