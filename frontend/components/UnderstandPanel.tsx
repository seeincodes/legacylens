"use client";

import { useState, type ReactNode } from "react";
import DependencyGraphView from "./DependencyGraphView";

// ── Types ──────────────────────────────────────────────

interface ExplainData {
  subroutine_name: string;
  routine_type: string | null;
  file_path: string;
  line_start: number;
  line_end: number;
  explanation: string;
  calls: string[];
  corrected_from?: string;
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
  corrected_from?: string;
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
  corrected_from?: string;
}

interface DocumentData {
  subroutine_name: string;
  documentation: string;
  corrected_from?: string;
}

interface TranslateData {
  subroutine_name: string;
  code: string;
  explanation: string;
  corrected_from?: string;
}

interface UseCasesData {
  subroutine_name: string;
  use_cases: string;
  typical_callers: string[];
  corrected_from?: string;
}

export type UnderstandFeature = "explain" | "eli5" | "dependencies" | "similar" | "document" | "translate" | "use-cases";

export type UnderstandResult =
  | { feature: "explain"; data: ExplainData }
  | { feature: "eli5"; data: ExplainData }
  | { feature: "dependencies"; data: DependencyData }
  | { feature: "similar"; data: SimilarData }
  | { feature: "document"; data: DocumentData }
  | { feature: "translate"; data: TranslateData }
  | { feature: "use-cases"; data: UseCasesData };

interface UnderstandPanelProps {
  result: UnderstandResult | null;
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
    /^>\s+/.test(trimmed) ||
    /^\|.+\|/.test(trimmed)
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

    // Markdown tables
    if (/^\|.+\|/.test(trimmed)) {
      const tableRows: string[] = [];
      while (i < lines.length && /^\|.+\|/.test(lines[i].trim())) {
        tableRows.push(lines[i].trim());
        i += 1;
      }
      // Parse header, separator, and body rows
      const parseRow = (row: string) =>
        row.split("|").slice(1, -1).map((c) => c.trim());
      const header = tableRows.length > 0 ? parseRow(tableRows[0]) : [];
      const isSeparator = (row: string) => /^\|[\s:-]+\|/.test(row);
      const bodyStart = tableRows.length > 1 && isSeparator(tableRows[1]) ? 2 : 1;
      const bodyRows = tableRows.slice(bodyStart).filter((r) => !isSeparator(r));

      elements.push(
        <div key={`tbl-${i}`} className="overflow-x-auto my-2">
          <table
            className="w-full text-xs border-collapse"
            style={{ fontFamily: "var(--font-jetbrains-mono)" }}
          >
            {header.length > 0 && (
              <thead>
                <tr>
                  {header.map((h, ci) => (
                    <th
                      key={ci}
                      className="text-left px-3 py-2 font-bold"
                      style={{
                        borderBottom: "2px solid var(--paper-grid)",
                        color: "var(--ink)",
                        fontFamily: "var(--font-architects-daughter)",
                        fontSize: "0.8rem",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
            )}
            <tbody>
              {bodyRows.map((row, ri) => {
                const cells = parseRow(row);
                return (
                  <tr key={ri}>
                    {cells.map((cell, ci) => (
                      <td
                        key={ci}
                        className="px-3 py-1.5"
                        style={{
                          borderBottom: "1px dashed var(--paper-grid)",
                          color: ci === 0 ? "var(--chalk-purple)" : "var(--ink)",
                          fontFamily: ci === 0 ? "var(--font-jetbrains-mono)" : "var(--font-crimson-pro)",
                          fontSize: ci === 0 ? "0.75rem" : "0.85rem",
                          fontWeight: ci === 0 ? 600 : 400,
                        }}
                      >
                        {renderInline(cell, `tbl-${i}-${ri}-${ci}`)}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
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
  const [viewMode, setViewMode] = useState<"list" | "graph">("graph");

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-faint)" }}>
          View:
        </span>
        <div className="flex rounded-lg overflow-hidden border" style={{ borderColor: "var(--paper-grid)" }}>
          <button
            type="button"
            onClick={() => setViewMode("list")}
            className="px-3 py-1.5 text-xs transition-colors"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              background: viewMode === "list" ? "var(--chalk-blue)" : "var(--paper)",
              color: viewMode === "list" ? "white" : "var(--ink-light)",
            }}
          >
            List
          </button>
          <button
            type="button"
            onClick={() => setViewMode("graph")}
            className="px-3 py-1.5 text-xs transition-colors border-l"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              borderColor: "var(--paper-grid)",
              background: viewMode === "graph" ? "var(--chalk-blue)" : "var(--paper)",
              color: viewMode === "graph" ? "white" : "var(--ink-light)",
            }}
          >
            Graph
          </button>
        </div>
      </div>
      {viewMode === "list" ? (
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
      ) : (
        <DependencyGraphView key={data.root} data={data} />
      )}
    </div>
  );
}

function SimilarView({ data }: { data: SimilarData }) {
  return (
    <div className="space-y-2.5">
      {data.similar.map((s, i) => {
        const typeStyle = TYPE_STYLES[s.routine_type || ""] || { color: "var(--ink-light)", bg: "var(--paper-dark)" };
        const scorePercent = Math.min(s.relevance_score * 100, 100);
        const scoreColor = scorePercent > 70 ? "var(--chalk-green)"
          : scorePercent > 40 ? "var(--chalk-amber)" : "var(--chalk-pink)";

        return (
          <div
            key={i}
            className="rounded-lg p-3"
            style={{
              border: "1px solid var(--paper-grid)",
              background: "var(--paper)",
            }}
          >
            {/* Header row: name, type badge, score */}
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="text-base font-bold truncate"
                  style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
                >
                  {s.subroutine_name || "Unknown"}
                </span>
                {s.routine_type && (
                  <span
                    className="math-tag shrink-0"
                    style={{ color: typeStyle.color, background: typeStyle.bg, border: `1px solid ${typeStyle.color}` }}
                  >
                    {s.routine_type}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <div className="w-16 h-2 rounded-full overflow-hidden" style={{ background: "var(--paper-dark)" }}>
                  <div className="h-full rounded-full transition-all" style={{ width: `${scorePercent}%`, background: scoreColor }} />
                </div>
                <span
                  className="text-xs font-bold min-w-[2.5rem] text-right"
                  style={{ fontFamily: "var(--font-jetbrains-mono)", color: scoreColor }}
                >
                  {scorePercent.toFixed(0)}%
                </span>
              </div>
            </div>
            {/* File path */}
            <div
              className="text-xs mb-1.5"
              style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}
            >
              {s.file_path}
            </div>
            {/* Code preview */}
            {s.content_preview && (
              <div
                className="text-xs leading-relaxed line-clamp-3 rounded px-2.5 py-2"
                style={{
                  fontFamily: "var(--font-jetbrains-mono)",
                  color: "var(--ink-light)",
                  background: "var(--paper-dark)",
                  whiteSpace: "pre-wrap",
                }}
              >
                {s.content_preview}
              </div>
            )}
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
  // Split documentation into sections by ## headings for card-based layout
  const sections = splitIntoSections(data.documentation);

  if (sections.length === 0) {
    return (
      <div className="answer-markdown text-sm leading-relaxed"
        style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink)" }}>
        {renderMarkdown(data.documentation)}
      </div>
    );
  }

  const SECTION_ICONS: Record<string, string> = {
    "what it does": "\u2139\uFE0F",
    "parameters": "\u2699\uFE0F",
    "how it works": "\u{1F527}",
    "return values": "\u21A9\uFE0F",
    "related routines": "\u{1F517}",
  };

  return (
    <div className="space-y-3">
      {sections.map((section, idx) => {
        const icon = SECTION_ICONS[section.title.toLowerCase()] || "";
        return (
          <div
            key={idx}
            className="rounded-lg overflow-hidden"
            style={{
              border: "1px solid var(--paper-grid)",
              background: "var(--paper)",
            }}
          >
            <div
              className="px-4 py-2"
              style={{
                background: "var(--paper-dark)",
                borderBottom: "1px dashed var(--paper-grid)",
              }}
            >
              <h3
                className="text-sm font-bold"
                style={{
                  fontFamily: "var(--font-architects-daughter)",
                  color: "var(--ink)",
                }}
              >
                {icon} {section.title}
              </h3>
            </div>
            <div
              className="px-4 py-3 answer-markdown text-sm leading-relaxed"
              style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink)" }}
            >
              {renderMarkdown(section.content)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function splitIntoSections(markdown: string): { title: string; content: string }[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const sections: { title: string; content: string }[] = [];
  let currentTitle = "";
  let currentLines: string[] = [];

  for (const line of lines) {
    const match = line.trim().match(/^##\s+(.+)$/);
    if (match) {
      if (currentTitle && currentLines.length > 0) {
        sections.push({ title: currentTitle, content: currentLines.join("\n").trim() });
      }
      currentTitle = match[1];
      currentLines = [];
    } else if (currentTitle) {
      currentLines.push(line);
    }
  }
  if (currentTitle && currentLines.length > 0) {
    sections.push({ title: currentTitle, content: currentLines.join("\n").trim() });
  }

  return sections;
}

function TranslateView({ data }: { data: TranslateData }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (data.code) {
      navigator.clipboard.writeText(data.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-3">
      {data.explanation && (
        <div className="answer-markdown text-sm leading-relaxed" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink)" }}>
          {renderMarkdown(data.explanation)}
        </div>
      )}
      {data.code && (
        <div
          className="rounded-lg overflow-hidden"
          style={{ border: "1px solid var(--paper-grid)" }}
        >
          <div
            className="flex items-center justify-between px-3 py-1.5"
            style={{
              background: "var(--paper-dark)",
              borderBottom: "1px solid var(--paper-grid)",
            }}
          >
            <span
              className="text-xs font-bold"
              style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}
            >
              Python equivalent
            </span>
            <button
              type="button"
              onClick={handleCopy}
              className="text-xs px-2 py-0.5 rounded transition-colors"
              style={{
                fontFamily: "var(--font-jetbrains-mono)",
                color: copied ? "var(--chalk-green)" : "var(--ink-faint)",
                background: copied ? "var(--chalk-green-light)" : "transparent",
                border: `1px solid ${copied ? "var(--chalk-green)" : "var(--paper-grid)"}`,
              }}
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <pre
            className="px-4 py-3 overflow-x-auto text-xs leading-relaxed"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink)",
              background: "var(--paper)",
              margin: 0,
            }}
          >
            <code>{data.code}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

function UseCasesView({ data }: { data: UseCasesData }) {
  return (
    <div className="space-y-3">
      <div className="answer-markdown text-sm leading-relaxed" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink)" }}>
        {renderMarkdown(data.use_cases)}
      </div>
      {data.typical_callers.length > 0 && (
        <div>
          <span className="text-xs font-bold" style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}>Typical callers:</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {data.typical_callers.map((c) => (
              <span key={c} className="math-tag" style={{ color: "var(--chalk-purple)", background: "var(--chalk-purple-light)", border: "1px solid var(--chalk-purple)" }}>{c}</span>
            ))}
          </div>
        </div>
      )}
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
  translate: "Generating Python equivalent…",
  "use-cases": "Finding use cases…",
};

// ── Main component ──

export default function UnderstandPanel({ result, isLoading, feature }: UnderstandPanelProps) {
  return (
    <div className="px-4 sm:px-5 py-4" style={{ borderTop: "2px dashed var(--paper-grid)" }}>
      {isLoading ? (
        <div className="loading-card p-3 space-y-2.5">
          <div className="flex items-center gap-2">
            <span
              className="inline-block w-2 h-2 rounded-full cursor-blink"
              style={{ background: "var(--chalk-amber)" }}
            />
            <span
              className="text-sm"
              style={{
                fontFamily: "var(--font-crimson-pro)",
                color: "var(--ink-light)",
                fontStyle: "italic",
              }}
            >
              {LOADING_LABELS[feature]}
            </span>
          </div>
          <div className="math-solve-card">
            <div className="math-load-formula">{`f(${feature}) -> structured_answer`}</div>
            <div className="math-load-track">
              <div className="math-load-fill" />
            </div>
          </div>
        </div>
      ) : result ? (
        <>
          {"corrected_from" in result.data && result.data.corrected_from && (
            <div
              className="mb-3 px-3 py-2 rounded-lg text-sm"
              style={{
                fontFamily: "var(--font-crimson-pro)",
                color: "var(--chalk-blue)",
                background: "var(--chalk-blue-light)",
                border: "1px solid var(--chalk-blue)",
              }}
            >
              Showing results for <strong>{"subroutine_name" in result.data ? result.data.subroutine_name : result.data.root}</strong> (you searched for &quot;{result.data.corrected_from}&quot;)
            </div>
          )}
          {result.feature === "explain" && <ExplainView data={result.data} />}
          {result.feature === "eli5" && <ELI5View data={result.data} />}
          {result.feature === "dependencies" && <DependencyView data={result.data} />}
          {result.feature === "similar" && <SimilarView data={result.data} />}
          {result.feature === "document" && <DocumentView data={result.data} />}
          {result.feature === "translate" && <TranslateView data={result.data} />}
          {result.feature === "use-cases" && <UseCasesView data={result.data} />}
        </>
      ) : null}
    </div>
  );
}
