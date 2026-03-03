"use client";

import type { ReactNode } from "react";

// ── Types ──────────────────────────────────────────────

interface ExplainData {
  subroutine_name: string;
  routine_type: string | null;
  file_path: string;
  line_start: number;
  line_end: number;
  explanation: string;
  calls: string[];
}

interface DependencyNode {
  name: string;
  routine_type: string | null;
  file_path: string | null;
  calls: string[];
  depth: number;
}

interface DependencyData {
  root: string;
  nodes: DependencyNode[];
  max_depth: number;
}

interface SimilarRoutine {
  subroutine_name: string | null;
  routine_type: string | null;
  file_path: string;
  relevance_score: number;
  content_preview: string;
}

interface SimilarData {
  subroutine_name: string;
  similar: SimilarRoutine[];
}

interface DocumentData {
  subroutine_name: string;
  documentation: string;
}

export type UnderstandFeature = "explain" | "eli5" | "dependencies" | "similar" | "document";

export type UnderstandResult =
  | { feature: "explain"; data: ExplainData }
  | { feature: "eli5"; data: ExplainData }
  | { feature: "dependencies"; data: DependencyData }
  | { feature: "similar"; data: SimilarData }
  | { feature: "document"; data: DocumentData };

interface UnderstandPanelProps {
  result: UnderstandResult;
  isLoading: boolean;
  feature: UnderstandFeature;
}

// ── Inline markdown (reused pattern from AnswerPanel) ──

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const inlinePattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
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

    if (!trimmed) { i += 1; continue; }

    if (trimmed.startsWith("```")) {
      const language = trimmed.slice(3).trim();
      i += 1;
      const codeLines: string[] = [];
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i += 1;
      }
      if (i < lines.length) i += 1;
      elements.push(
        <div key={`code-${i}`} className="answer-codeblock">
          {language && <div className="answer-code-lang">{language}</div>}
          <pre><code>{codeLines.join("\n")}</code></pre>
        </div>
      );
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const text = headingMatch[2];
      const content = renderInline(text, `h-${i}`);
      if (level === 1) elements.push(<h1 key={`h1-${i}`}>{content}</h1>);
      else if (level === 2) elements.push(<h2 key={`h2-${i}`}>{content}</h2>);
      else if (level === 3) elements.push(<h3 key={`h3-${i}`}>{content}</h3>);
      else elements.push(<h4 key={`h4-${i}`}>{content}</h4>);
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
          {items.map((item, idx) => <li key={idx}>{renderInline(item, `ul-${i}-${idx}`)}</li>)}
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
          {items.map((item, idx) => <li key={idx}>{renderInline(item, `ol-${i}-${idx}`)}</li>)}
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
        <blockquote key={`q-${i}`}>{renderInline(quoteLines.join(" "), `q-${i}`)}</blockquote>
      );
      continue;
    }

    const paragraphLines: string[] = [trimmed];
    i += 1;
    while (i < lines.length) {
      const next = lines[i];
      if (!next.trim()) { i += 1; break; }
      if (isBlockStart(next)) break;
      paragraphLines.push(next.trim());
      i += 1;
    }
    elements.push(<p key={`p-${i}`}>{renderInline(paragraphLines.join(" "), `p-${i}`)}</p>);
  }

  return elements;
}

// ── Feature type colors ──

const TYPE_STYLES: Record<string, { color: string; bg: string }> = {
  blas: { color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
  driver: { color: "var(--chalk-pink)", bg: "var(--chalk-pink-light)" },
  computational: { color: "var(--chalk-green)", bg: "var(--chalk-green-light)" },
};

// ── Renderers per feature ──

function ExplainView({ data }: { data: ExplainData }) {
  return (
    <div className="space-y-3">
      <div className="answer-markdown text-sm leading-relaxed"
        style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink)" }}>
        {renderMarkdown(data.explanation)}
      </div>
      {data.calls.length > 0 && (
        <div>
          <span className="text-xs font-bold"
            style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}>
            Calls:
          </span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {data.calls.map((c) => (
              <span key={c} className="math-tag"
                style={{ color: "var(--chalk-purple)", background: "var(--chalk-purple-light)", border: "1px solid var(--chalk-purple)" }}>
                {c}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DependencyView({ data }: { data: DependencyData }) {
  return (
    <div className="space-y-1">
      {data.nodes.map((node, i) => {
        const typeStyle = TYPE_STYLES[node.routine_type || ""] || { color: "var(--ink-light)", bg: "var(--paper-dark)" };
        return (
          <div key={i} className="flex items-center gap-2 py-1"
            style={{ paddingLeft: `${node.depth * 24}px` }}>
            {node.depth > 0 && (
              <span style={{ color: "var(--ink-faint)", fontFamily: "var(--font-jetbrains-mono)", fontSize: "0.75rem" }}>
                └─
              </span>
            )}
            <span className="text-sm font-bold"
              style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}>
              {node.name}
            </span>
            {node.routine_type && (
              <span className="math-tag"
                style={{ color: typeStyle.color, background: typeStyle.bg, border: `1px solid ${typeStyle.color}` }}>
                {node.routine_type}
              </span>
            )}
            {node.file_path && (
              <span className="text-xs"
                style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}>
                {node.file_path}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SimilarView({ data }: { data: SimilarData }) {
  return (
    <div className="space-y-2">
      {data.similar.map((s, i) => {
        const typeStyle = TYPE_STYLES[s.routine_type || ""] || { color: "var(--ink-light)", bg: "var(--paper-dark)" };
        const scorePercent = Math.min(s.relevance_score * 100, 100);
        const scoreColor = scorePercent > 70 ? "var(--chalk-green)"
          : scorePercent > 40 ? "var(--chalk-amber)" : "var(--chalk-pink)";

        return (
          <div key={i} className="flex items-start gap-3 py-2"
            style={{ borderBottom: i < data.similar.length - 1 ? "1px dashed var(--paper-grid)" : "none" }}>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm font-bold"
                  style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}>
                  {s.subroutine_name || "Unknown"}
                </span>
                {s.routine_type && (
                  <span className="math-tag"
                    style={{ color: typeStyle.color, background: typeStyle.bg, border: `1px solid ${typeStyle.color}` }}>
                    {s.routine_type}
                  </span>
                )}
                <span className="text-xs"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}>
                  {s.file_path}
                </span>
              </div>
              <p className="text-xs mt-1 line-clamp-2"
                style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-light)" }}>
                {s.content_preview}
              </p>
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <div className="w-12 h-1.5 rounded-full overflow-hidden" style={{ background: "var(--paper-dark)" }}>
                <div className="h-full rounded-full" style={{ width: `${scorePercent}%`, background: scoreColor }} />
              </div>
              <span className="text-xs" style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}>
                {scorePercent.toFixed(0)}%
              </span>
            </div>
          </div>
        );
      })}
      {data.similar.length === 0 && (
        <p className="text-sm" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}>
          No similar routines found.
        </p>
      )}
    </div>
  );
}

function ELI5View({ data }: { data: ExplainData }) {
  return (
    <div className="space-y-3">
      <div
        className="answer-markdown text-base leading-relaxed rounded-lg p-4"
        style={{
          fontFamily: "var(--font-architects-daughter)",
          color: "var(--ink)",
          background: "var(--chalk-amber-light)",
          border: "2px dashed var(--chalk-amber)",
        }}
      >
        {renderMarkdown(data.explanation)}
      </div>
    </div>
  );
}

function DocumentView({ data }: { data: DocumentData }) {
  return (
    <div className="answer-markdown text-sm leading-relaxed"
      style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink)" }}>
      {renderMarkdown(data.documentation)}
    </div>
  );
}

// ── Loading state ──

const LOADING_LABELS: Record<UnderstandFeature, string> = {
  explain: "Generating explanation…",
  eli5: "Explaining in simple words…",
  dependencies: "Tracing call chain…",
  similar: "Finding similar routines…",
  document: "Generating documentation…",
};

// ── Main component ──

export default function UnderstandPanel({ result, isLoading, feature }: UnderstandPanelProps) {
  return (
    <div className="px-4 sm:px-5 py-4" style={{ borderTop: "2px dashed var(--paper-grid)" }}>
      {isLoading ? (
        <div className="flex items-center gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full cursor-blink"
            style={{ background: "var(--chalk-amber)" }} />
          <span className="text-sm"
            style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)", fontStyle: "italic" }}>
            {LOADING_LABELS[feature]}
          </span>
        </div>
      ) : result ? (
        <>
          {result.feature === "explain" && <ExplainView data={result.data} />}
          {result.feature === "eli5" && <ELI5View data={result.data} />}
          {result.feature === "dependencies" && <DependencyView data={result.data} />}
          {result.feature === "similar" && <SimilarView data={result.data} />}
          {result.feature === "document" && <DocumentView data={result.data} />}
        </>
      ) : null}
    </div>
  );
}
