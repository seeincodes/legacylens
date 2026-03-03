interface CodeBlockProps {
  code: string;
  filePath: string;
  lineStart: number;
  lineEnd: number;
}

export default function CodeBlock({
  code,
  filePath,
  lineStart,
  lineEnd,
}: CodeBlockProps) {
  return (
    <div className="overflow-hidden" style={{ background: "var(--code-bg)", borderRadius: "0 0 10px 10px" }}>
      {/* File header */}
      <div
        className="px-4 py-2 flex justify-between items-center text-xs"
        style={{
          fontFamily: "var(--font-jetbrains-mono)",
          background: "var(--code-line)",
          color: "var(--code-comment)",
        }}
      >
        <span className="flex items-center gap-2">
          <span style={{ color: "var(--code-keyword)" }}>file:</span>
          <span style={{ color: "var(--code-text)" }}>{filePath}</span>
        </span>
        <span>
          L{lineStart}–{lineEnd}
        </span>
      </div>

      {/* Code with line numbers */}
      <pre
        className="p-4 text-sm overflow-x-auto leading-relaxed"
        style={{
          color: "var(--code-text)",
          fontFamily: "var(--font-jetbrains-mono)",
        }}
      >
        <code>
          {code.split("\n").map((line, i) => (
            <div key={i} className="flex hover:bg-white/5 -mx-4 px-4 transition-colors">
              <span
                className="select-none pr-4 text-right shrink-0"
                style={{
                  color: "var(--code-comment)",
                  minWidth: "3rem",
                  borderRight: "1px solid var(--code-line)",
                  marginRight: "1rem",
                  opacity: 0.6,
                }}
              >
                {lineStart + i}
              </span>
              <span>{line}</span>
            </div>
          ))}
        </code>
      </pre>
    </div>
  );
}
