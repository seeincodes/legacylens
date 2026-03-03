import CodeBlock from "./CodeBlock";

interface Chunk {
  file_path: string;
  line_start: number;
  line_end: number;
  subroutine_name: string | null;
  routine_type: string | null;
  content: string;
  relevance_score: number;
}

interface ResultsListProps {
  chunks: Chunk[];
}

const TYPE_STYLES: Record<string, { color: string; bg: string }> = {
  blas: { color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
  driver: { color: "var(--chalk-pink)", bg: "var(--chalk-pink-light)" },
  computational: { color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
};

export default function ResultsList({ chunks }: ResultsListProps) {
  if (chunks.length === 0) return null;

  return (
    <div className="w-full space-y-4 fade-in-up">
      {/* Simple section header */}
      <div className="flex items-center gap-3">
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
          className="text-xs"
          style={{
            fontFamily: "var(--font-jetbrains-mono)",
            color: "var(--ink-faint)",
          }}
        >
          {chunks.length} result{chunks.length !== 1 && "s"}
        </span>
      </div>

      {chunks.map((chunk, i) => {
        const typeStyle = TYPE_STYLES[chunk.routine_type || ""] || {
          color: "var(--ink-light)",
          bg: "var(--paper-dark)",
        };

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
              className="px-5 py-3 flex items-center justify-between"
              style={{ borderBottom: "1px dashed var(--paper-grid)" }}
            >
              <div className="flex items-center gap-3">
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
                  className="text-xl font-bold"
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

              {/* Relevance score */}
              <div className="flex items-center gap-2">
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
              </div>
            </div>

            <CodeBlock
              code={chunk.content}
              filePath={chunk.file_path}
              lineStart={chunk.line_start}
              lineEnd={chunk.line_end}
            />
          </div>
        );
      })}
    </div>
  );
}
