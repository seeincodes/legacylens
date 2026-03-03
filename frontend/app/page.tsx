"use client";

import { useState } from "react";
import QueryInput from "@/components/QueryInput";
import AnswerPanel from "@/components/AnswerPanel";
import ResultsList from "@/components/ResultsList";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Chunk {
  file_path: string;
  line_start: number;
  line_end: number;
  subroutine_name: string | null;
  routine_type: string | null;
  content: string;
  relevance_score: number;
}

export default function Home() {
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);

  const handleQuery = async (query: string) => {
    setIsLoading(true);
    setIsStreaming(true);
    setAnswer("");
    setChunks([]);

    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5 }),
      });

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
          }
        }
      }
    } catch (error) {
      console.error("Query failed:", error);
      setAnswer("Could not reach the backend. Is the server running?");
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
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
        <QueryInput onSubmit={handleQuery} isLoading={isLoading} />
        <AnswerPanel answer={answer} isStreaming={isStreaming} />
        <ResultsList chunks={chunks} />
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
