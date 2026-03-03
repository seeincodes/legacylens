"use client";

interface AnswerPanelProps {
  answer: string;
  isStreaming: boolean;
}

export default function AnswerPanel({ answer, isStreaming }: AnswerPanelProps) {
  if (!answer) return null;

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
          className="text-base leading-relaxed whitespace-pre-wrap"
          style={{
            fontFamily: "var(--font-crimson-pro)",
            color: "var(--ink)",
            fontSize: "1.05rem",
          }}
        >
          {answer}
          {isStreaming && (
            <span
              className="cursor-blink inline-block w-0.5 h-5 ml-0.5 align-text-bottom rounded-sm"
              style={{ background: "var(--chalk-blue)" }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
