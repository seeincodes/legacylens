"use client";

const LEGEND_ITEMS = [
  { label: "Driver", color: "#4a6fa5" },
  { label: "Computational", color: "#3a8a5c" },
  { label: "BLAS", color: "#c8860a" },
  { label: "Other", color: "#a89e8c" },
];

export default function MapLegend() {
  return (
    <div
      className="absolute bottom-4 left-4 z-40 px-3 py-2 rounded-lg flex flex-col gap-1.5"
      style={{
        background: "var(--paper)",
        border: "2px solid var(--paper-grid)",
        boxShadow: "2px 2px 0 var(--paper-dark)",
      }}
    >
      <span
        className="text-xs font-bold mb-0.5"
        style={{ fontFamily: "var(--font-architects-daughter)", color: "var(--ink)" }}
      >
        Routine Type
      </span>
      {LEGEND_ITEMS.map((item) => (
        <div key={item.label} className="flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-full shrink-0"
            style={{ background: item.color }}
          />
          <span
            className="text-xs"
            style={{ fontFamily: "var(--font-crimson-pro)", color: "var(--ink-light)" }}
          >
            {item.label}
          </span>
        </div>
      ))}
    </div>
  );
}
