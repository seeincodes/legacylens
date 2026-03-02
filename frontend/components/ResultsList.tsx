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

export default function ResultsList({ chunks }: ResultsListProps) {
  if (chunks.length === 0) return null;

  return (
    <div className="w-full max-w-3xl space-y-4">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
        Retrieved Code ({chunks.length} results)
      </h2>
      {chunks.map((chunk, i) => (
        <div key={i} className="border border-gray-200 rounded-lg overflow-hidden shadow-sm">
          <div className="px-4 py-2 bg-gray-50 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-700">
                {chunk.subroutine_name || "Unknown"}
              </span>
              {chunk.routine_type && (
                <span className="text-xs px-2 py-0.5 bg-blue-100 text-blue-700 rounded-full">
                  {chunk.routine_type}
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">
              Score: {chunk.relevance_score.toFixed(4)}
            </span>
          </div>
          <CodeBlock
            code={chunk.content}
            filePath={chunk.file_path}
            lineStart={chunk.line_start}
            lineEnd={chunk.line_end}
          />
        </div>
      ))}
    </div>
  );
}
