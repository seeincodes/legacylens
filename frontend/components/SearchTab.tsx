"use client";

import { useState, useEffect } from "react";
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
  blas_level: string | null;
  content: string;
  relevance_score: number;
  relevance_label: string;
}

interface SearchTabProps {
  linkedRoutine?: string | null;
  linkedAction?: string | null;
  initialQuery?: string | null;
}

export default function SearchTab({ linkedRoutine, linkedAction, initialQuery }: SearchTabProps) {
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

  useEffect(() => {
    if (linkedRoutine) {
      handleQuery(`What does ${linkedRoutine} do?`);
    }
  }, [linkedRoutine, linkedAction]); // eslint-disable-line react-hooks/exhaustive-deps

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
    <div className="w-full flex flex-col items-center px-4 gap-5">
      <div className="w-full max-w-3xl flex flex-col gap-5">
        <div className={`flex flex-col gap-5 transition-opacity duration-200 ${isLoading ? "opacity-50 pointer-events-none" : ""}`}>
          <QueryInput onSubmit={handleQuery} isLoading={isLoading} expand={expandSearch} onExpandChange={setExpandSearch} brief={briefMode} onBriefChange={setBriefMode} initialQuery={initialQuery} />
          <SearchFilters routineType={routineType} precisionType={precisionType} onRoutineTypeChange={setRoutineType} onPrecisionTypeChange={setPrecisionType} disabled={isLoading} />
        </div>
        <AnswerPanel answer={answer} isStreaming={isStreaming} hasUnverified={hasUnverified} />
        {!isStreaming && (
          <ResultsList chunks={chunks} isLoading={isLoading} error={queryError} hasSearched={hasSearched} autoUnderstand={linkedRoutine && linkedAction ? { routine: linkedRoutine, action: linkedAction } : undefined} />
        )}
      </div>
    </div>
  );
}
