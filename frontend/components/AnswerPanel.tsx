"use client";

interface AnswerPanelProps {
  answer: string;
  isStreaming: boolean;
}

export default function AnswerPanel({ answer, isStreaming }: AnswerPanelProps) {
  if (!answer) return null;

  return (
    <div className="w-full max-w-3xl bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Answer {isStreaming && <span className="animate-pulse">...</span>}
      </h2>
      <div className="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
        {answer}
      </div>
    </div>
  );
}
