import type { ReactNode } from "react";

interface CodeBlockProps {
  code: string;
  filePath: string;
  lineStart: number;
  lineEnd: number;
  focusStartLine?: number;
  focusEndLine?: number;
}

const FORTRAN_KEYWORDS = new Set([
  "SUBROUTINE",
  "FUNCTION",
  "PROGRAM",
  "MODULE",
  "END",
  "CALL",
  "IF",
  "THEN",
  "ELSE",
  "ENDIF",
  "DO",
  "CONTINUE",
  "RETURN",
  "STOP",
  "GOTO",
  "IMPLICIT",
  "NONE",
  "INTEGER",
  "REAL",
  "DOUBLE",
  "PRECISION",
  "COMPLEX",
  "LOGICAL",
  "CHARACTER",
  "PARAMETER",
  "DIMENSION",
  "COMMON",
  "DATA",
  "SAVE",
  "EXTERNAL",
  "INTRINSIC",
  "SELECT",
  "CASE",
  "WHERE",
  "ALLOCATE",
  "DEALLOCATE",
  "USE",
  "ONLY",
]);

const TOKEN_RE = /('[^']*'|"[^"]*"|\b\d+(?:\.\d*)?(?:[dDeE][+-]?\d+)?\b|\b[A-Za-z_][A-Za-z0-9_]*\b)/g;

function splitFortranComment(line: string): { code: string; comment: string } {
  // Fixed-form comment lines start with C/c/* in column 1.
  if (/^[cC*]/.test(line)) {
    return { code: "", comment: line };
  }
  const trimmed = line.trimStart();
  if (trimmed.startsWith("!")) {
    return { code: "", comment: line };
  }

  let inSingleQuote = false;
  let inDoubleQuote = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === "'" && !inDoubleQuote) {
      inSingleQuote = !inSingleQuote;
    } else if (ch === '"' && !inSingleQuote) {
      inDoubleQuote = !inDoubleQuote;
    } else if (ch === "!" && !inSingleQuote && !inDoubleQuote) {
      return {
        code: line.slice(0, i),
        comment: line.slice(i),
      };
    }
  }

  return { code: line, comment: "" };
}

function highlightFortranLine(line: string): ReactNode[] {
  const { code, comment } = splitFortranComment(line);

  if (!code) {
    return [<span key="comment-only" style={{ color: "var(--code-comment)" }}>{comment}</span>];
  }

  const nodes: ReactNode[] = [];
  let lastIdx = 0;

  for (const match of code.matchAll(TOKEN_RE)) {
    const token = match[0];
    const idx = match.index ?? 0;
    if (idx > lastIdx) {
      nodes.push(<span key={`plain-${idx}`}>{code.slice(lastIdx, idx)}</span>);
    }

    if ((token.startsWith("'") && token.endsWith("'")) || (token.startsWith('"') && token.endsWith('"'))) {
      nodes.push(<span key={`str-${idx}`} style={{ color: "var(--code-string)" }}>{token}</span>);
    } else if (/^\d/.test(token)) {
      nodes.push(<span key={`num-${idx}`} style={{ color: "var(--code-number)" }}>{token}</span>);
    } else if (FORTRAN_KEYWORDS.has(token.toUpperCase())) {
      nodes.push(<span key={`kw-${idx}`} style={{ color: "var(--code-keyword)" }}>{token}</span>);
    } else {
      nodes.push(<span key={`id-${idx}`}>{token}</span>);
    }
    lastIdx = idx + token.length;
  }

  if (lastIdx < code.length) {
    nodes.push(<span key={`plain-tail-${lastIdx}`}>{code.slice(lastIdx)}</span>);
  }
  if (comment) {
    nodes.push(<span key="comment-tail" style={{ color: "var(--code-comment)" }}>{comment}</span>);
  }

  return nodes;
}

export default function CodeBlock({
  code,
  filePath,
  lineStart,
  lineEnd,
  focusStartLine,
  focusEndLine,
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
        className="p-3 sm:p-4 text-xs sm:text-sm overflow-x-auto leading-relaxed"
        style={{
          color: "var(--code-text)",
          fontFamily: "var(--font-jetbrains-mono)",
        }}
      >
        <code>
          {code.split("\n").map((line, i) => {
            const currentLine = lineStart + i;
            const isFocused =
              typeof focusStartLine === "number" &&
              typeof focusEndLine === "number" &&
              currentLine >= focusStartLine &&
              currentLine <= focusEndLine;

            return (
            <div
              key={i}
              className="flex hover:bg-white/5 -mx-3 sm:-mx-4 px-3 sm:px-4 transition-colors"
              style={isFocused ? { background: "rgba(74, 111, 165, 0.14)" } : undefined}
            >
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
                {currentLine}
              </span>
              <span>{highlightFortranLine(line)}</span>
            </div>
            );
          })}
        </code>
      </pre>
    </div>
  );
}
