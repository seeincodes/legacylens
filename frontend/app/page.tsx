"use client";

import { useState } from "react";
import Link from "next/link";
import QueryInput from "@/components/QueryInput";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsList from "@/components/ResultsList";
import SearchFilters from "@/components/SearchFilters";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export default function Home() {
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [expandSearch, setExpandSearch] = useState(false);
  const [briefMode, setBriefMode] = useState(false);
  const [hasUnverified, setHasUnverified] = useState(false);
  const [routineType, setRoutineType] = useState("");
  const [precisionType, setPrecisionType] = useState("");

  const handleQuery = async (query: string) => {
    setHasSearched(true);
    setIsLoading(true);
    setIsStreaming(true);
    setQueryError("");
    setAnswer("");
    setChunks([]);
    setHasUnverified(false);

    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          top_k: 5,
          expand: expandSearch,
          brief: briefMode,
          routine_type: routineType || null,
          precision_type: precisionType || null,
        }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        const detail = data?.detail || `Request failed (${response.status})`;
        throw new Error(detail);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line || !line.startsWith("data: ")) continue;
          let data;
          try {
            data = JSON.parse(line.slice(6));
          } catch {
            continue;
          }

          if (data.type === "chunks") {
            setChunks(data.chunks);
            setIsLoading(false);
          } else if (data.type === "token") {
            setAnswer((prev) => prev + data.token);
          } else if (data.type === "done") {
            setIsStreaming(false);
            if (data.answer !== undefined) setAnswer(data.answer);
            setHasUnverified(data.has_unverified === true);
          }
        }
      }
    } catch (error) {
      console.error("Query failed:", error);
      const message =
        error instanceof Error
          ? error.message
          : "Could not reach the backend. Is the server running?";
      setQueryError(message);
      setAnswer("");
      setChunks([]);
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  return (
    <main className="relative z-10 min-h-screen flex flex-col items-center px-4 py-12 gap-6">
      {/* Header */}
      <div className="flex items-start justify-center mt-2 mb-1 gap-4">
        <div className="flex-1" />
        <div className="text-center flex-1">
          <h1
          className="text-5xl md:text-6xl"
          style={{
            fontFamily: "var(--font-architects-daughter)",
            color: "var(--ink)",
          }}
        >
          LegacyLens
        </h1>
        <p
          className="mt-2 text-base"
          style={{
            fontFamily: "var(--font-crimson-pro)",
            color: "var(--ink-light)",
            fontStyle: "italic",
          }}
        >
          Explore the LAPACK Fortran codebase with natural language
        </p>
        </div>
        <Link
          href="/stats"
          className="flex-1 text-right inline-flex items-center justify-end gap-2 px-4 py-2 rounded-2xl font-bold text-sm"
          style={{
            fontFamily: "var(--font-architects-daughter)",
            color: "var(--chalk-blue)",
            background: "var(--chalk-blue-light)",
            border: "2px dashed var(--chalk-blue)",
            boxShadow: "1px 1px 0 rgba(74,111,165,0.2)",
          }}
        >
          <span style={{ fontSize: "1.1em" }}>📊</span>
          Stats
        </Link>
      </div>

      {/* Query + Results */}
      <div className="w-full max-w-3xl flex flex-col gap-5">
        <div
          className={`flex flex-col gap-5 transition-opacity duration-200 ${isLoading ? "opacity-50 pointer-events-none" : ""}`}
        >
          <QueryInput
            onSubmit={handleQuery}
            isLoading={isLoading}
            expand={expandSearch}
            onExpandChange={setExpandSearch}
            brief={briefMode}
            onBriefChange={setBriefMode}
          />
          <SearchFilters
            routineType={routineType}
            precisionType={precisionType}
            onRoutineTypeChange={setRoutineType}
            onPrecisionTypeChange={setPrecisionType}
            disabled={isLoading}
          />
        </div>
        <AnswerPanel answer={answer} isStreaming={isStreaming} hasUnverified={hasUnverified} />
        {!isStreaming && (
          <ResultsList
            chunks={chunks}
            isLoading={isLoading}
            error={queryError}
            hasSearched={hasSearched}
          />
        )}
      </div>

      {/* Footer */}
      <footer
        className="mt-auto pt-10 text-center text-xs"
        style={{
          fontFamily: "var(--font-crimson-pro)",
          color: "var(--ink-faint)",
        }}
      >
        LAPACK — Linear Algebra PACKage — Univ. of Tennessee, UC Berkeley, NAG Ltd.
      </footer>
    </main>
  );
}
