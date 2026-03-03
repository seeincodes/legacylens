"use client";

import { useState } from "react";
import QueryInput from "@/components/QueryInput";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsList from "@/components/ResultsList";
import SearchFilters from "@/components/SearchFilters";
import UnderstandPanel from "@/components/UnderstandPanel";

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
  const [routineType, setRoutineType] = useState("");
  const [precisionType, setPrecisionType] = useState("");
  const [analysisResult, setAnalysisResult] = useState<any>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisType, setAnalysisType] = useState("");
  const [dataUsageInput, setDataUsageInput] = useState("");
  const [showDataUsageInput, setShowDataUsageInput] = useState(false);

  const handleQuery = async (query: string) => {
    setHasSearched(true);
    setIsLoading(true);
    setIsStreaming(true);
    setQueryError("");
    setAnswer("");
    setChunks([]);
    setAnalysisResult(null);
    setAnalysisType("");

    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          top_k: 5,
          expand: expandSearch,
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
          } else if (data.type === "analysis") {
            setAnalysisResult(data);
            setAnalysisType(data.analysis_type);
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

  const handleAnalysis = async (type: string, variableName?: string) => {
    setAnalysisLoading(true);
    setAnalysisType(type);
    setAnalysisResult(null);

    const endpointMap: Record<string, string> = {
      entry_points: "/api/understand/entry-points",
      data_usage: "/api/understand/data-usage",
      io_operations: "/api/understand/io-operations",
      error_patterns: "/api/understand/error-patterns",
    };

    try {
      const body: any = {};
      if (type === "data_usage" && variableName) {
        body.variable_name = variableName;
      }
      const response = await fetch(`${API_URL}${endpointMap[type]}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) throw new Error(`Request failed (${response.status})`);
      const data = await response.json();
      setAnalysisResult(data);
    } catch (err) {
      console.error("Analysis failed:", err);
    } finally {
      setAnalysisLoading(false);
    }
  };

  return (
    <main className="relative z-10 min-h-screen flex flex-col items-center px-4 py-12 gap-6">
      {/* Header */}
      <div className="text-center mt-2 mb-1">
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

      {/* Query + Results */}
      <div className="w-full max-w-3xl flex flex-col gap-5">
        <QueryInput
          onSubmit={handleQuery}
          isLoading={isLoading}
          expand={expandSearch}
          onExpandChange={setExpandSearch}
        />
        <SearchFilters
          routineType={routineType}
          precisionType={precisionType}
          onRoutineTypeChange={setRoutineType}
          onPrecisionTypeChange={setPrecisionType}
          disabled={isLoading}
        />
        {/* Quick Analysis */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-3 flex-wrap">
            <span
              className="text-sm font-bold"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--ink-light)",
              }}
            >
              Quick Analysis:
            </span>
            <button
              className="text-xs px-3 py-1.5 rounded-full border transition-opacity hover:opacity-80 disabled:opacity-40"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--chalk-pink)",
                borderColor: "var(--chalk-pink)",
                background: "var(--chalk-pink-light)",
              }}
              disabled={analysisLoading}
              onClick={() => handleAnalysis("entry_points")}
            >
              Entry Points
            </button>
            <button
              className="text-xs px-3 py-1.5 rounded-full border transition-opacity hover:opacity-80 disabled:opacity-40"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--chalk-purple)",
                borderColor: "var(--chalk-purple)",
                background: "var(--chalk-purple-light)",
              }}
              disabled={analysisLoading}
              onClick={() => setShowDataUsageInput((prev) => !prev)}
            >
              Data Usage
            </button>
            <button
              className="text-xs px-3 py-1.5 rounded-full border transition-opacity hover:opacity-80 disabled:opacity-40"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--chalk-blue)",
                borderColor: "var(--chalk-blue)",
                background: "var(--chalk-blue-light)",
              }}
              disabled={analysisLoading}
              onClick={() => handleAnalysis("io_operations")}
            >
              I/O Operations
            </button>
            <button
              className="text-xs px-3 py-1.5 rounded-full border transition-opacity hover:opacity-80 disabled:opacity-40"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--chalk-amber)",
                borderColor: "var(--chalk-amber)",
                background: "var(--chalk-amber-light)",
              }}
              disabled={analysisLoading}
              onClick={() => handleAnalysis("error_patterns")}
            >
              Error Patterns
            </button>
          </div>
          {showDataUsageInput && (
            <div className="flex items-center gap-2 ml-0 sm:ml-[108px]">
              <input
                type="text"
                placeholder="Variable name (e.g. INFO, LDA)"
                value={dataUsageInput}
                onChange={(e) => setDataUsageInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && dataUsageInput.trim()) {
                    handleAnalysis("data_usage", dataUsageInput.trim());
                    setShowDataUsageInput(false);
                  }
                }}
                className="text-xs px-3 py-1.5 rounded-full border outline-none"
                style={{
                  fontFamily: "var(--font-jetbrains-mono)",
                  color: "var(--ink)",
                  borderColor: "var(--chalk-purple)",
                  background: "var(--paper)",
                }}
              />
              <button
                className="text-xs px-3 py-1.5 rounded-full border transition-opacity hover:opacity-80 disabled:opacity-40"
                style={{
                  fontFamily: "var(--font-architects-daughter)",
                  color: "var(--chalk-purple)",
                  borderColor: "var(--chalk-purple)",
                  background: "var(--chalk-purple-light)",
                }}
                disabled={!dataUsageInput.trim() || analysisLoading}
                onClick={() => {
                  if (dataUsageInput.trim()) {
                    handleAnalysis("data_usage", dataUsageInput.trim());
                    setShowDataUsageInput(false);
                  }
                }}
              >
                Search
              </button>
            </div>
          )}
        </div>

        {/* Analysis Results */}
        {(analysisLoading || analysisResult) && (
          <div className="math-card overflow-hidden">
            <div className="px-4 sm:px-5 py-3" style={{ borderBottom: "1px dashed var(--paper-grid)" }}>
              <span className="text-sm font-bold" style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--ink)",
              }}>
                {analysisType === "entry_points" ? "Entry Points" :
                 analysisType === "data_usage" ? "Data Usage" :
                 analysisType === "io_operations" ? "I/O Operations" :
                 analysisType === "error_patterns" ? "Error Patterns" : "Analysis"}
              </span>
            </div>
            <UnderstandPanel
              feature={analysisType as any}
              result={analysisResult ? { feature: analysisType as any, data: analysisResult } : null!}
              isLoading={analysisLoading}
            />
          </div>
        )}

        <AnswerPanel answer={answer} isStreaming={isStreaming} />
        <ResultsList
          chunks={chunks}
          isLoading={isLoading}
          error={queryError}
          hasSearched={hasSearched}
        />
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
