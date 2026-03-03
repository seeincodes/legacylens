"use client";

import { useState } from "react";

interface QueryInputProps {
  onSubmit: (query: string) => void;
  expand: boolean;
  onExpandChange: (enabled: boolean) => void;
  isLoading: boolean;
}

export default function QueryInput({ onSubmit, expand, onExpandChange, isLoading }: QueryInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSubmit(query.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="math-card p-5">
        <div className="flex gap-3">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about LAPACK... e.g. &quot;What does DGESV do?&quot;"
            className="flex-1 px-4 py-2.5 text-lg rounded-lg border-2 transition-all"
            style={{
              fontFamily: "var(--font-architects-daughter)",
              color: "var(--ink)",
              background: "white",
              borderColor: "var(--paper-grid)",
            }}
            disabled={isLoading}
          />

          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-6 py-2.5 text-base rounded-lg font-bold transition-all duration-200 shrink-0"
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

        {/* Example queries */}
        <div className="flex gap-2 mt-3 flex-wrap">
          {[
            "What does DGESV do?",
            "How does LU factorization work?",
            "Explain eigenvalue decomposition",
          ].map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                setQuery(example);
                if (!isLoading) onSubmit(example);
              }}
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

        <div className="mt-4 pt-3 flex items-center justify-end" style={{ borderTop: "1px dashed var(--paper-grid)" }}>
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
          </label>
        </div>
      </div>
    </form>
  );
}
