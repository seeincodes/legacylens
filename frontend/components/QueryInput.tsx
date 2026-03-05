"use client";

import { useState, useEffect } from "react";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  expand: boolean;
  onExpandChange: (enabled: boolean) => void;
  brief: boolean;
  onBriefChange: (enabled: boolean) => void;
  isLoading: boolean;
  initialQuery?: string | null;
}

export default function QueryInput({ onSubmit, expand, onExpandChange, brief, onBriefChange, isLoading, initialQuery }: QueryInputProps) {
  const [query, setQuery] = useState(initialQuery || "");

  useEffect(() => {
    if (initialQuery) setQuery(initialQuery);
  }, [initialQuery]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="math-card p-5">
        <div className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about LAPACK... e.g. &quot;What does DGESV do?&quot;"
            className="flex-1 px-4 py-2.5 text-base sm:text-lg rounded-lg border-2 transition-all"
            style={{
              fontFamily: "var(--font-architects-daughter)",
              color: isLoading ? "var(--ink-faint)" : "var(--ink)",
              background: isLoading ? "var(--paper-dark)" : "white",
              borderColor: "var(--paper-grid)",
            }}
            disabled={isLoading}
          />

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-6 py-2.5 text-base rounded-lg font-bold transition-all duration-200 shrink-0 sm:w-auto w-full"
            style={{
              fontFamily: "var(--font-architects-daughter)",
              background:
                isLoading || !query.trim()
                  ? "var(--paper-grid)"
                  : "var(--chalk-blue)",
              color:
                isLoading || !query.trim()
                  ? "var(--ink-faint)"
                  : "white",
              cursor:
                isLoading || !query.trim() ? "not-allowed" : "pointer",
              boxShadow:
                isLoading || !query.trim()
                  ? "none"
                  : "2px 2px 0 rgba(74,111,165,0.3)",
            }}
          >
            {isLoading ? "Searching..." : "Search"}
          </button>
        </div>

        {/* Suggestions — populate search bar only, don't auto-submit */}
        <div className="flex gap-2 mt-3 flex-wrap">
          <span
            className="text-xs w-full"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
            }}
          >
            Suggestions:
          </span>
          {[
            "What does DGESV do?",
            "How does LU factorization work?",
            "Explain eigenvalue decomposition",
          ].map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setQuery(example)}
              className="text-xs px-3 py-1 rounded-full transition-colors duration-150"
              style={{
                fontFamily: "var(--font-jetbrains-mono)",
                color: "var(--chalk-purple)",
                background: "var(--chalk-purple-light)",
                border: "1px solid transparent",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = "var(--chalk-purple)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = "transparent";
              }}
            >
              {example}
            </button>
          ))}
        </div>

        <div className="mt-4 pt-3 flex items-center justify-end gap-6 flex-wrap" style={{ borderTop: "1px dashed var(--paper-grid)" }}>
          <label
            className="inline-flex items-center gap-2 text-sm cursor-pointer"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-light)",
            }}
          >
            <input
              type="checkbox"
              checked={brief}
              onChange={(e) => onBriefChange(e.target.checked)}
              disabled={isLoading}
              className="w-4 h-4 rounded"
              style={{ accentColor: "var(--chalk-blue)" }}
            />
            Brief answer
            <span className="relative group">
              <span
                className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold cursor-help"
                style={{
                  color: "var(--chalk-blue)",
                  background: "var(--chalk-blue-light)",
                  border: "1px solid var(--chalk-blue)",
                }}
              >
                ?
              </span>
              <span
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs whitespace-normal w-56 text-left opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-10 pointer-events-none"
                style={{
                  fontFamily: "var(--font-crimson-pro)",
                  color: "var(--ink)",
                  background: "white",
                  border: "1px solid var(--paper-grid)",
                  boxShadow: "2px 2px 0 rgba(0,0,0,0.05)",
                }}
              >
                Get concise 1–3 sentence answers for simple lookups.
              </span>
            </span>
          </label>
          <label
            className="inline-flex items-center gap-2 text-sm cursor-pointer"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-light)",
            }}
          >
            <input
              type="checkbox"
              checked={expand}
              onChange={(e) => onExpandChange(e.target.checked)}
              disabled={isLoading}
              className="w-4 h-4 rounded"
              style={{ accentColor: "var(--chalk-blue)" }}
            />
            Expand search
            <span
              className="relative group"
            >
              <span
                className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold cursor-help"
                style={{
                  color: "var(--chalk-blue)",
                  background: "var(--chalk-blue-light)",
                  border: "1px solid var(--chalk-blue)",
                }}
              >
                ?
              </span>
              <span
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs whitespace-normal w-56 text-left opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-10 pointer-events-none"
                style={{
                  fontFamily: "var(--font-crimson-pro)",
                  color: "var(--ink)",
                  background: "white",
                  border: "1px solid var(--paper-grid)",
                  boxShadow: "2px 2px 0 rgba(0,0,0,0.05)",
                }}
              >
                Uses AI to rephrase your query into 2-3 variants for better recall. Finds more results but takes slightly longer.
              </span>
            </span>
          </label>
        </div>
      </div>
    </form>
  );
}
