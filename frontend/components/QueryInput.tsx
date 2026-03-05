"use client";

import { useState, useEffect, useRef, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const QUESTION_TEMPLATES = [
  (name: string) => `What does ${name} do?`,
  (name: string) => `Explain how ${name} works`,
  (name: string) => `What routines call ${name}?`,
  (name: string) => `What are the parameters of ${name}?`,
  (name: string) => `How is ${name} used in practice?`,
];

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
  const [randomSuggestions, setRandomSuggestions] = useState<string[]>([]);
  const [shuffling, setShuffling] = useState(false);
  const cachedRoutines = useRef<string[]>([]);

  const fetchRandomSuggestions = useCallback(async () => {
    setShuffling(true);
    try {
      if (cachedRoutines.current.length === 0) {
        const res = await fetch(`${API_URL}/api/graph`);
        if (!res.ok) throw new Error("Failed to fetch graph");
        const data = await res.json();
        cachedRoutines.current = data.nodes.map((n: { id: string }) => n.id);
      }
      const routines = cachedRoutines.current;
      const picked = new Set<string>();
      while (picked.size < 3 && picked.size < routines.length) {
        picked.add(routines[Math.floor(Math.random() * routines.length)]);
      }
      const suggestions = Array.from(picked).map((name) => {
        const template = QUESTION_TEMPLATES[Math.floor(Math.random() * QUESTION_TEMPLATES.length)];
        return template(name);
      });
      setRandomSuggestions(suggestions);
    } catch {
      setRandomSuggestions([]);
    } finally {
      setShuffling(false);
    }
  }, []);

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
          <div className="relative flex-1">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about LAPACK... e.g. &quot;What does DGESV do?&quot;"
              className="w-full px-4 py-2.5 text-base sm:text-lg rounded-lg border-2 transition-all"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: isLoading ? "var(--ink-faint)" : "var(--ink)",
                background: isLoading ? "var(--paper-dark)" : "white",
                borderColor: isLoading ? "var(--chalk-amber)" : "var(--paper-grid)",
                paddingRight: isLoading ? "2.5rem" : "1rem",
              }}
              disabled={isLoading}
            />
            {isLoading && (
              <div
                className="absolute right-3 top-1/2 -translate-y-1/2"
              >
                <svg
                  className="animate-spin"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  style={{ color: "var(--chalk-amber)" }}
                >
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
                </svg>
              </div>
            )}
          </div>

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
        <div className="flex gap-2 mt-3 flex-wrap items-center">
          <span
            className="text-xs w-full"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
            }}
          >
            Suggestions:
          </span>
          {(randomSuggestions.length > 0
            ? randomSuggestions
            : [
                "How does LAPACK solve a system of linear equations?",
                "What routines compute singular value decomposition?",
                "What's the difference between single and double precision routines?",
              ]
          ).map((example) => (
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
          <button
            type="button"
            onClick={fetchRandomSuggestions}
            disabled={shuffling}
            className="text-xs px-3 py-1 rounded-full transition-colors duration-150"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--chalk-blue)",
              background: "var(--chalk-blue-light)",
              border: "1px solid transparent",
              cursor: shuffling ? "wait" : "pointer",
              opacity: shuffling ? 0.6 : 1,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "var(--chalk-blue)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "transparent";
            }}
          >
            {shuffling ? "Loading..." : "Surprise me"}
          </button>
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
