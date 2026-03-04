interface SearchFiltersProps {
  routineType: string;
  precisionType: string;
  onRoutineTypeChange: (value: string) => void;
  onPrecisionTypeChange: (value: string) => void;
  disabled?: boolean;
}

const ROUTINE_OPTIONS = [
  { label: "All Routines", value: "" },
  { label: "BLAS", value: "blas" },
  { label: "Driver", value: "driver" },
  { label: "Computational", value: "computational" },
];

const PRECISION_OPTIONS = [
  { label: "All Precision", value: "" },
  { label: "Single", value: "single" },
  { label: "Double", value: "double" },
  { label: "Complex", value: "complex" },
  { label: "Double Complex", value: "double_complex" },
];

export default function SearchFilters({
  routineType,
  precisionType,
  onRoutineTypeChange,
  onPrecisionTypeChange,
  disabled = false,
}: SearchFiltersProps) {
  return (
    <div className="w-full math-card p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="flex flex-col gap-1">
          <span
            className="text-xs"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Routine Type
          </span>
          <select
            value={routineType}
            onChange={(e) => onRoutineTypeChange(e.target.value)}
            disabled={disabled}
            className="px-3 py-2 rounded-lg border-2 text-sm transition-colors"
            style={{
              fontFamily: "var(--font-crimson-pro)",
              color: disabled ? "var(--ink-faint)" : "var(--ink)",
              background: disabled ? "var(--paper-dark)" : "white",
              borderColor: "var(--paper-grid)",
            }}
          >
            {ROUTINE_OPTIONS.map((option) => (
              <option key={option.value || "all-routine"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="flex flex-col gap-1">
          <span
            className="text-xs"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Precision
          </span>
          <select
            value={precisionType}
            onChange={(e) => onPrecisionTypeChange(e.target.value)}
            disabled={disabled}
            className="px-3 py-2 rounded-lg border-2 text-sm transition-colors"
            style={{
              fontFamily: "var(--font-crimson-pro)",
              color: disabled ? "var(--ink-faint)" : "var(--ink)",
              background: disabled ? "var(--paper-dark)" : "white",
              borderColor: "var(--paper-grid)",
            }}
          >
            {PRECISION_OPTIONS.map((option) => (
              <option key={option.value || "all-precision"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </div>
  );
}
