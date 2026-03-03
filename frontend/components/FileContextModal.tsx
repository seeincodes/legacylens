"use client";

import { useEffect, useMemo, useState } from "react";
import CodeBlock from "./CodeBlock";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FileContextModalProps {
  isOpen: boolean;
  filePath: string;
  focusStartLine: number;
  focusEndLine: number;
  onClose: () => void;
}

export default function FileContextModal({
  isOpen,
  filePath,
  focusStartLine,
  focusEndLine,
  onClose,
}: FileContextModalProps) {
  const [content, setContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const controller = new AbortController();
    const fetchFile = async () => {
      setIsLoading(true);
      setError("");
      try {
        const response = await fetch(`${API_URL}/api/file?path=${encodeURIComponent(filePath)}`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          throw new Error(data?.detail || `Failed to load file (${response.status})`);
        }
        const data = await response.json();
        setContent(data.content || "");
      } catch (err) {
        if (controller.signal.aborted) {
          return;
        }
        const message = err instanceof Error ? err.message : "Could not load file context.";
        setError(message);
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    };

    fetchFile();
    return () => controller.abort();
  }, [isOpen, filePath]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [isOpen, onClose]);

  const lineCount = useMemo(() => {
    if (!content) {
      return 1;
    }
    return content.split("\n").length;
  }, [content]);

  if (!isOpen) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 bg-black/45 p-3 sm:p-6 flex items-start sm:items-center justify-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-6xl max-h-[92vh] math-card overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="px-4 sm:px-5 py-3 flex items-start justify-between gap-3"
          style={{ borderBottom: "1px dashed var(--paper-grid)" }}
        >
          <div className="min-w-0">
            <h3
              className="text-base sm:text-lg font-bold truncate"
              style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
            >
              Full File Context
            </h3>
            <p
              className="text-xs sm:text-sm truncate"
              style={{ fontFamily: "var(--font-jetbrains-mono)", color: "var(--ink-faint)" }}
            >
              {filePath} (matched lines: {focusStartLine}-{focusEndLine})
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1 rounded-full text-xs border"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-light)",
              borderColor: "var(--paper-grid)",
              background: "white",
            }}
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-auto p-3 sm:p-4" style={{ background: "var(--paper-dark)" }}>
          {isLoading && (
            <div className="math-card p-4">
              <p style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}>
                Loading file context...
              </p>
            </div>
          )}
          {!isLoading && error && (
            <div className="math-card p-4" style={{ borderColor: "var(--chalk-pink)" }}>
              <p style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--chalk-pink)" }}>
                {error}
              </p>
            </div>
          )}
          {!isLoading && !error && (
            <CodeBlock
              code={content}
              filePath={filePath}
              lineStart={1}
              lineEnd={lineCount}
              focusStartLine={focusStartLine}
              focusEndLine={focusEndLine}
            />
          )}
        </div>
      </div>
    </div>
  );
}
