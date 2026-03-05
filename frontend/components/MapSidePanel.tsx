"use client";

import Link from "next/link";

interface MapSidePanelProps {
  nodeId: string;
  routineType: string | null;
  filePath: string | null;
  callees: string[];
  callers: string[];
  onNodeSelect: (id: string) => void;
  onClose: () => void;
}

const TYPE_BADGE_STYLES: Record<string, { color: string; bg: string; border: string }> = {
  driver: { color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)", border: "var(--chalk-blue)" },
  computational: { color: "var(--chalk-green)", bg: "var(--chalk-green-light)", border: "var(--chalk-green)" },
  blas: { color: "var(--chalk-amber)", bg: "var(--chalk-amber-light)", border: "var(--chalk-amber)" },
};

const ACTION_BUTTONS = [
  { action: "explain", label: "Explain", color: "var(--chalk-blue)", bg: "var(--chalk-blue-light)" },
];

export default function MapSidePanel({
  nodeId,
  routineType,
  filePath,
  callees,
  callers,
  onNodeSelect,
  onClose,
}: MapSidePanelProps) {
  const badge = TYPE_BADGE_STYLES[routineType || ""];
  const uniqueCallees = [...new Set(callees)];
  const uniqueCallers = [...new Set(callers)];

  return (
    <div
      className="w-80 shrink-0 overflow-y-auto flex flex-col"
      style={{
        background: "var(--paper)",
        borderLeft: "2px solid var(--paper-grid)",
        minHeight: "100%",
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between px-4 pt-4 pb-3" style={{ borderBottom: "1px dashed var(--paper-grid)" }}>
        <div className="min-w-0">
          <h2
            className="text-lg font-bold truncate"
            style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink)" }}
          >
            {nodeId}
          </h2>
          {routineType && badge && (
            <span
              className="inline-block mt-1 px-2 py-0.5 rounded-full text-xs font-medium"
              style={{ color: badge.color, background: badge.bg, border: `1px solid ${badge.border}` }}
            >
              {routineType}
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-lg leading-none px-1 shrink-0"
          style={{ color: "var(--ink-faint)", fontFamily: "var(--font-architects-daughter)" }}
          aria-label="Close panel"
        >
          ×
        </button>
      </div>

      {/* File path */}
      {filePath && (
        <div className="px-4 py-2" style={{ borderBottom: "1px dashed var(--paper-grid)" }}>
          <span className="text-xs" style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}>
            {filePath}
          </span>
        </div>
      )}

      {/* Calls (callees) */}
      <div className="px-4 py-3" style={{ borderBottom: "1px dashed var(--paper-grid)" }}>
        <h3
          className="text-xs font-bold mb-2"
          style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}
        >
          Calls ({uniqueCallees.length})
        </h3>
        {uniqueCallees.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {uniqueCallees.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => onNodeSelect(c)}
                className="px-2 py-0.5 rounded text-xs hover:opacity-80 transition-opacity cursor-pointer"
                style={{
                  fontFamily: "var(--font-jetbrains-mono)",
                  color: "var(--chalk-purple)",
                  background: "var(--chalk-purple-light)",
                  border: "1px solid var(--chalk-purple)",
                }}
              >
                {c}
              </button>
            ))}
          </div>
        ) : (
          <span className="text-xs" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-faint)" }}>
            No outgoing calls
          </span>
        )}
      </div>

      {/* Called by (callers) */}
      <div className="px-4 py-3" style={{ borderBottom: "1px dashed var(--paper-grid)" }}>
        <h3
          className="text-xs font-bold mb-2"
          style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}
        >
          Called by ({uniqueCallers.length})
        </h3>
        {uniqueCallers.length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {uniqueCallers.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => onNodeSelect(c)}
                className="px-2 py-0.5 rounded text-xs hover:opacity-80 transition-opacity cursor-pointer"
                style={{
                  fontFamily: "var(--font-jetbrains-mono)",
                  color: "var(--chalk-blue)",
                  background: "var(--chalk-blue-light)",
                  border: "1px solid var(--chalk-blue)",
                }}
              >
                {c}
              </button>
            ))}
          </div>
        ) : (
          <span className="text-xs" style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-faint)" }}>
            No incoming calls
          </span>
        )}
      </div>

      {/* Action buttons */}
      <div className="px-4 py-3">
        <h3
          className="text-xs font-bold mb-2"
          style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink-light)" }}
        >
          Explore
        </h3>
        <div className="flex flex-wrap gap-2">
          {ACTION_BUTTONS.map((btn) => (
            <Link
              key={btn.action}
              href={`/?routine=${encodeURIComponent(nodeId)}&action=${btn.action}`}
              className="px-3 py-1.5 rounded-lg text-xs font-medium hover:opacity-80 transition-opacity"
              style={{
                fontFamily: "var(--font-architects-daughter)",
                color: btn.color,
                background: btn.bg,
                border: `1px solid ${btn.color}`,
              }}
            >
              {btn.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
