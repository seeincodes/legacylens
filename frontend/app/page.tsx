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
          if (!line.startsWith("data: ")) continue;
          const data = JSON.parse(line.slice(6));

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
      setAnswer("Error: Failed to query the backend. Is the server running?");
    } finally {
      setIsLoading(false);
      setIsStreaming(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 flex flex-col items-center px-4 py-12 gap-6">
      <div className="text-center mb-4">
        <h1 className="text-3xl font-bold text-gray-900">LegacyLens</h1>
        <p className="text-gray-500 mt-1">
          RAG-powered search for the LAPACK Fortran codebase
        </p>
      </div>

      <QueryInput onSubmit={handleQuery} isLoading={isLoading} />
      <AnswerPanel answer={answer} isStreaming={isStreaming} />
      <ResultsList chunks={chunks} />
    </main>
  );
}
