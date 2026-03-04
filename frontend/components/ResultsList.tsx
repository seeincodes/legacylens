"use client";

import { useEffect, useState, useCallback } from "react";
import CodeBlock from "./CodeBlock";
import UnderstandPanel from "./UnderstandPanel";
import type { UnderstandFeature, UnderstandResult } from "./UnderstandPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LAPACK_GITHUB_BASE =
  "https://github.com/Reference-LAPACK/lapack/blob/master";

interface Chunk {
  file_path: string;
  line_start: number;
  line_end: number;
  subroutine_name: string | null;
  routine_type: string | null;
  content: string;
  relevance_score: number;
  relevance_label: string;
}

interface ResultsListProps {
  chunks: Chunk[];
  isLoading: boolean;
  error: string;
  hasSearched: boolean;
}

const TYPE_STYLES: Record<string, { color: string; bg: string }> = {
  blas: { color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
  driver: { color: "var(--chalk-pink)", bg: "var(--chalk-pink-light)" },
  computational: { color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
};

const UNDERSTAND_BUTTONS: { feature: UnderstandFeature; label: string; color: string; bg: string }[] = [
  { feature: "explain", label: "Explain", color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
  { feature: "eli5", label: "ELI5", color: "var(--chalk-pink)", bg: "var(--chalk-pink-light)" },
  { feature: "dependencies", label: "Deps", color: "var(--chalk-purple)", bg: "var(--chalk-purple-light)" },
  { feature: "similar", label: "Similar", color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
  { feature: "document", label: "Docs", color: "var(--chalk-amber)", bg: "var(--chalk-amber-light)" },
  { feature: "translate", label: "Translate", color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
  { feature: "use-cases", label: "Use cases", color: "var(--chalk-amber)", bg: "var(--chalk-amber-light)" },
];

const ENDPOINT_MAP: Record<UnderstandFeature, string> = {
  explain: "/api/understand/explain",
  eli5: "/api/understand/eli5",
  dependencies: "/api/understand/dependencies",
  similar: "/api/understand/similar",
  document: "/api/understand/document",
  translate: "/api/understand/translate",
  "use-cases": "/api/understand/use-cases",
};

interface UnderstandState {
  feature: UnderstandFeature | null;
  result: UnderstandResult | null;
  isLoading: boolean;
  error: string;
}

export default function ResultsList({ chunks, isLoading, error, hasSearched }: ResultsListProps) {
  const [expandedChunks, setExpandedChunks] = useState<Record<string, boolean>>({});
  const [understandState, setUnderstandState] = useState<Record<string, UnderstandState>>({});

  useEffect(() => {
    setExpandedChunks({});
    setUnderstandState({});
  }, [chunks]);

  const handleUnderstand = useCallback(async (chunkKey: string, subroutineName: string, feature: UnderstandFeature) => {
    const current = understandState[chunkKey];

    // Toggle off if same feature
    if (current?.feature === feature && !current.isLoading) {
      setUnderstandState((prev) => ({ ...prev, [chunkKey]: { feature: null, result: null, isLoading: false, error: "" } }));
      return;
    }

    setUnderstandState((prev) => ({
      ...prev,
      [chunkKey]: { feature, result: null, isLoading: true, error: "" },
    }));

    try {
      const response = await fetch(`${API_URL}${ENDPOINT_MAP[feature]}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subroutine_name: subroutineName }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(data?.detail || `Request failed (${response.status})`);
      }

      const data = await response.json();
      setUnderstandState((prev) => ({
        ...prev,
        [chunkKey]: { feature, result: { feature, data } as UnderstandResult, isLoading: false, error: "" },
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      setUnderstandState((prev) => ({
        ...prev,
        [chunkKey]: { feature, result: null, isLoading: false, error: message },
      }));
    }
  }, [understandState]);

  if (!hasSearched && chunks.length === 0 && !isLoading && !error) return null;

  return (
    <div className="w-full space-y-4 fade-in-up">
      {/* Section header */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <h2
          className="text-lg font-bold"
          style={{
            fontFamily: "var(--font-architects-daughter)",
            color: "var(--ink)",
          }}
        >
          Retrieved Code
        </h2>
        <span
          className="flex-1"
          style={{ borderBottom: "2px dashed var(--paper-grid)" }}
        />
        <span
          className="text-xs ml-auto"
          style={{
            fontFamily: "var(--font-jetbrains-mono)",
            color: "var(--ink-faint)",
          }}
        >
          {chunks.length} result{chunks.length !== 1 && "s"}
        </span>
      </div>

      {isLoading && (
        <div className="math-card p-4 space-y-3">
          <div className="flex items-center gap-2">
            <span
              className="inline-block w-2 h-2 rounded-full cursor-blink"
              style={{ background: "var(--chalk-blue)" }}
            />
            <p
              className="text-sm italic"
              style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
            >
              Searching and retrieving relevant code snippets...
            </p>
          </div>
          <div className="loading-card p-3 space-y-2">
            <div className="math-load-formula">{"f(query) -> retrieve(code_chunks)"}</div>
            <div className="math-load-track">
              <div className="math-load-fill" />
            </div>
          </div>
        </div>
      )}

      {!isLoading && error && (
        <div className="math-card p-4" style={{ borderColor: "var(--chalk-pink)" }}>
          <p
            className="text-sm"
            style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--chalk-pink)" }}
          >
            {error}
          </p>
        </div>
      )}

      {!isLoading && !error && hasSearched && chunks.length === 0 && (
        <div className="math-card p-4">
          <p
            className="text-sm"
            style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
          >
            No matching code chunks found for this query and filter combination.
          </p>
        </div>
      )}

      {chunks.map((chunk, i) => {
        const chunkKey = `${chunk.file_path}:${chunk.line_start}-${chunk.line_end}:${i}`;
        const isExpanded = !!expandedChunks[chunkKey];
        const typeStyle = TYPE_STYLES[chunk.routine_type || ""] || {
          color: "var(--ink-light)",
          bg: "var(--paper-dark)",
        };
        const uState = understandState[chunkKey];
        const hasSubroutine = !!chunk.subroutine_name;

        return (
          <div
            key={i}
            className="math-card overflow-hidden"
            style={{
              animation: `fadeInUp 0.4s ease-out forwards`,
              animationDelay: `${i * 80}ms`,
              opacity: 0,
            }}
          >
            {/* Chunk header */}
            <div
              className="px-4 sm:px-5 py-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
              style={{ borderBottom: "1px dashed var(--paper-grid)" }}
            >
              <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
                {/* Result number */}
                <span
                  className="text-xs font-bold w-5 h-5 flex items-center justify-center rounded-full"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono)",
                    color: "var(--chalk-blue)",
                    background: "var(--chalk-blue-light)",
                  }}
                >
                  {i + 1}
                </span>

                {/* Subroutine name */}
                <span
                  className="text-lg sm:text-xl font-bold"
                  style={{
                    fontFamily: "var(--font-architects-daughter)",
                    color: "var(--ink)",
                  }}
                >
                  {chunk.subroutine_name || "Unknown"}
                </span>

                {/* Routine type badge */}
                {chunk.routine_type && (
                  <span
                    className="math-tag"
                    style={{
                      color: typeStyle.color,
                      background: typeStyle.bg,
                      border: `1px solid ${typeStyle.color}`,
                    }}
                  >
                    {chunk.routine_type}
                  </span>
                )}
              </div>

              {/* Relevance score with label + per-card toggle */}
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono)",
                    color:
                      chunk.relevance_label === "High"
                        ? "var(--chalk-green)"
                        : chunk.relevance_label === "Medium"
                          ? "var(--chalk-amber)"
                          : "var(--chalk-pink)",
                    background:
                      chunk.relevance_label === "High"
                        ? "var(--chalk-green-light)"
                        : chunk.relevance_label === "Medium"
                          ? "var(--chalk-amber-light)"
                          : "var(--chalk-pink-light)",
                  }}
                >
                  {chunk.relevance_label}
                </span>
                <div
                  className="w-16 h-1.5 rounded-full overflow-hidden"
                  style={{ background: "var(--paper-dark)" }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.min(chunk.relevance_score * 100, 100)}%`,
                      background:
                        chunk.relevance_score > 0.7
                          ? "var(--chalk-green)"
                          : chunk.relevance_score > 0.4
                            ? "var(--chalk-amber)"
                            : "var(--chalk-pink)",
                    }}
                  />
                </div>
                <span
                  className="text-xs"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono)",
                    color: "var(--ink-faint)",
                  }}
                >
                  {(chunk.relevance_score * 100).toFixed(0)}%
                </span>
                <button
                  type="button"
                  onClick={() =>
                    setExpandedChunks((prev) => ({
                      ...prev,
                      [chunkKey]: !prev[chunkKey],
                    }))
                  }
                  className="text-xs px-2 py-0.5 rounded-full border transition-colors"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono)",
                    color: "var(--chalk-blue)",
                    borderColor: "var(--chalk-blue)",
                    background: "var(--chalk-blue-light)",
                  }}
                >
                  {isExpanded ? "Hide code" : "Show code"}
                </button>
                <a
                  href={`${LAPACK_GITHUB_BASE}/${chunk.file_path}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs px-2 py-0.5 rounded-full border transition-colors"
                  style={{
                    fontFamily: "var(--font-jetbrains-mono)",
                    color: "var(--chalk-purple)",
                    borderColor: "var(--chalk-purple)",
                    background: "var(--chalk-purple-light)",
                    textDecoration: "none",
                  }}
                >
                  View full file
                </a>
              </div>
            </div>

            {/* Code understanding action buttons */}
            {hasSubroutine && (
              <div
                className="px-4 sm:px-5 py-2 flex items-center gap-2 flex-wrap"
                style={{ borderBottom: "1px dashed var(--paper-grid)" }}
              >
                <span
                  className="text-xs mr-1"
                  style={{
                    fontFamily: "var(--font-architects-daughter)",
                    color: "var(--ink-faint)",
                  }}
                >
                  Understand:
                </span>
                {UNDERSTAND_BUTTONS.map((btn) => {
                  const isActive = uState?.feature === btn.feature && !uState?.error;
                  return (
                    <button
                      key={btn.feature}
                      type="button"
                      disabled={uState?.isLoading && uState?.feature !== btn.feature}
                      onClick={() => handleUnderstand(chunkKey, chunk.subroutine_name!, btn.feature)}
                      className="text-xs px-2 py-0.5 rounded-full border transition-colors"
                      style={{
                        fontFamily: "var(--font-jetbrains-mono)",
                        color: isActive ? "white" : btn.color,
                        borderColor: btn.color,
                        background: isActive ? btn.color : btn.bg,
                        opacity: uState?.isLoading && uState?.feature !== btn.feature ? 0.5 : 1,
                        cursor: uState?.isLoading && uState?.feature !== btn.feature ? "not-allowed" : "pointer",
                      }}
                    >
                      {uState?.isLoading && uState?.feature === btn.feature ? "…" : btn.label}
                    </button>
                  );
                })}
              </div>
            )}

            {isExpanded ? (
              <CodeBlock
                code={chunk.content}
                filePath={chunk.file_path}
                lineStart={chunk.line_start}
                lineEnd={chunk.line_end}
              />
            ) : (
              <div
                className="px-4 sm:px-5 py-3 text-sm"
                style={{
                  fontFamily: "var(--font-crimson-pro)",
                  color: "var(--ink-light)",
                }}
              >
                Code snippet collapsed.
              </div>
            )}

            {/* Understanding panel */}
            {uState?.feature && (uState.isLoading || uState.result || uState.error) && (
              uState.error ? (
                <div className="px-4 sm:px-5 py-3" style={{ borderTop: "2px dashed var(--paper-grid)" }}>
                  <p className="text-sm" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--chalk-pink)" }}>
                    {uState.error}
                  </p>
                </div>
              ) : (
                <UnderstandPanel
                  feature={uState.feature}
                  result={uState.result}
                  isLoading={uState.isLoading}
                />
              )
            )}
          </div>
        );
      })}

    </div>
  );
}
