"use client";

import type { ReactNode } from "react";

interface AnswerPanelProps {
  answer: string;
  isStreaming: boolean;
}

const CITATION_RE = /\[([^\]:]+):(\d+)(?:[-–](\d+))?\]/g;

function extractCitations(text: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  let m: RegExpExecArray | null;
  CITATION_RE.lastIndex = 0;
  while ((m = CITATION_RE.exec(text)) !== null) {
    const full = m[3] ? `${m[1]}:${m[2]}-${m[3]}` : `${m[1]}:${m[2]}`;
    if (!seen.has(full)) {
      seen.add(full);
      out.push(full);
    }
  }
  return out;
}

function SourceChip({ source }: { source: string }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold"
      style={{
        fontFamily: "var(--font-jetbrains-mono)",
        color: "white",
        background: "var(--chalk-blue)",
        border: "2px solid var(--chalk-blue)",
        fontSize: "0.9rem",
        boxShadow: "2px 2px 0 rgba(74,111,165,0.3)",
      }}
    >
      <span style={{ opacity: 0.9 }}>📄</span>
      {source}
    </span>
  );
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const inlinePattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]:]+:\d+(?:[-–]\d+)?\])/g;
  const parts = text.split(inlinePattern).filter(Boolean);

  return parts.map((part, idx) => {
    const key = `${keyPrefix}-${idx}`;
    if (part.startsWith("`") && part.endsWith("`")) {
      return <code key={key}>{part.slice(1, -1)}</code>;
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={key}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith("*") && part.endsWith("*")) {
      return <em key={key}>{part.slice(1, -1)}</em>;
    }
    if (/^\[[^\]:]+:\d+(?:[-–]\d+)?\]$/.test(part)) {
      return <SourceChip key={key} source={part.slice(1, -1)} />;
    }
    return <span key={key}>{part}</span>;
  });
}

function isBlockStart(line: string): boolean {
  const trimmed = line.trim();
  return (
    trimmed.startsWith("```") ||
    /^#{1,4}\s+/.test(trimmed) ||
    /^[-*]\s+/.test(trimmed) ||
    /^\d+\.\s+/.test(trimmed) ||
    /^>\s+/.test(trimmed)
  );
}

function renderMarkdown(markdown: string): ReactNode[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const elements: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith("```")) {
      const language = trimmed.slice(3).trim();
      i += 1;
      const codeLines: string[] = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i += 1;
      }
      if (i < lines.length && lines[i].trim().startsWith("```")) {
        i += 1;
      }

      elements.push(
        <div key={`code-${i}`} className="answer-codeblock">
          {language && <div className="answer-code-lang">{language}</div>}
          <pre>
            <code>{codeLines.join("\n")}</code>
          </pre>
        </div>
      );
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = headingMatch[2];
      const content = renderInline(text, `h-${i}`);
      if (level === 1) {
        elements.push(<h1 key={`h1-${i}`}>{content}</h1>);
      } else if (level === 2) {
        elements.push(<h2 key={`h2-${i}`}>{content}</h2>);
      } else if (level === 3) {
        elements.push(<h3 key={`h3-${i}`}>{content}</h3>);
      } else {
        elements.push(<h4 key={`h4-${i}`}>{content}</h4>);
      }
      i += 1;
      continue;
    }

    if (/^[-*]\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^[-*]\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^[-*]\s+/, ""));
        i += 1;
      }
      elements.push(
        <ul key={`ul-${i}`}>
          {items.map((item, idx) => (
            <li key={`ul-${i}-${idx}`}>{renderInline(item, `ul-${i}-${idx}`)}</li>
          ))}
        </ul>
      );
      continue;
    }

    if (/^\d+\.\s+/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i].trim())) {
        items.push(lines[i].trim().replace(/^\d+\.\s+/, ""));
        i += 1;
      }
      elements.push(
        <ol key={`ol-${i}`}>
          {items.map((item, idx) => (
            <li key={`ol-${i}-${idx}`}>{renderInline(item, `ol-${i}-${idx}`)}</li>
          ))}
        </ol>
      );
      continue;
    }

    if (/^>\s+/.test(trimmed)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s+/.test(lines[i].trim())) {
        quoteLines.push(lines[i].trim().replace(/^>\s+/, ""));
        i += 1;
      }
      elements.push(
        <blockquote key={`quote-${i}`}>
          {renderInline(quoteLines.join(" "), `q-${i}`)}
        </blockquote>
      );
      continue;
    }

    const paragraphLines: string[] = [trimmed];
    i += 1;
    while (i < lines.length) {
      const next = lines[i];
      if (!next.trim()) {
        i += 1;
        break;
      }
      if (isBlockStart(next)) {
        break;
      }
      paragraphLines.push(next.trim());
      i += 1;
    }
    elements.push(
      <p key={`p-${i}`}>
        {renderInline(paragraphLines.join(" "), `p-${i}`)}
      </p>
    );
  }

  return elements;
}

export default function AnswerPanel({ answer, isStreaming }: AnswerPanelProps) {
  if (!answer) return null;

  const sources = extractCitations(answer);

  return (
    <div className="w-full math-card fade-in-up overflow-hidden">
      {/* Header */}
      <div
        className="px-5 py-2 flex items-center justify-between"
        style={{
          borderBottom: "2px solid var(--paper-grid)",
        }}
      >
        <span
          className="text-sm font-bold"
          style={{
            fontFamily: "var(--font-architects-daughter)",
            color: "var(--ink)",
          }}
        >
          Answer
        </span>
        {isStreaming && (
          <span
            className="flex items-center gap-1.5 text-xs"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
            }}
          >
            <span
              className="inline-block w-1.5 h-1.5 rounded-full cursor-blink"
              style={{ background: "var(--chalk-amber)" }}
            />
            streaming
          </span>
        )}
      </div>

      {/* Answer body */}
      <div className="p-5">
        <div
          className="answer-markdown text-base leading-relaxed"
          style={{
            fontFamily: "var(--font-crimson-pro)",
            color: "var(--ink)",
            fontSize: "1.05rem",
          }}
        >
          {renderMarkdown(answer)}
          {isStreaming && (
            <span
              className="cursor-blink inline-block w-0.5 h-5 ml-0.5 align-text-bottom rounded-sm"
              style={{ background: "var(--chalk-blue)" }}
            />
          )}
        </div>

        {/* Sources section — prominent chips for all citations */}
        {sources.length > 0 && (
          <div
            className="mt-4 pt-4 flex flex-wrap gap-2"
            style={{ borderTop: "2px dashed var(--paper-grid)" }}
          >
            <span
              className="text-xs font-bold"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: "var(--ink-light)",
                width: "100%",
                marginBottom: "2px",
              }}
            >
              Sources
            </span>
            {sources.map((s, i) => (
              <SourceChip key={`${s}-${i}`} source={s} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
