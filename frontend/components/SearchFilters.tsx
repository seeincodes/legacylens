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
            className="text-xs inline-flex items-center gap-1.5"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Routine Type
            <span className="relative group">
              <span
                className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold cursor-help"
                style={{
                  color: "var(--chalk-blue)",
                  background: "var(--chalk-blue-light)",
                  border: "1px solid var(--chalk-blue)",
                }}
              >
                ?
              </span>
              <span
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs whitespace-normal w-56 text-left opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-10 pointer-events-none"
                style={{
                  fontFamily: "var(--font-crimson-pro)",
                  color: "var(--ink)",
                  background: "white",
                  border: "1px solid var(--paper-grid)",
                  boxShadow: "2px 2px 0 rgba(0,0,0,0.05)",
                }}
              >
                BLAS: low-level ops (DAXPY, DGEMM). Driver: high-level solvers (DGESV, DSYEV). Computational: core algorithms (DGETRF, DPOTRF).
              </span>
            </span>
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
            className="text-xs inline-flex items-center gap-1.5"
            style={{
              fontFamily: "var(--font-jetbrains-mono)",
              color: "var(--ink-faint)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            Precision
            <span className="relative group">
              <span
                className="inline-flex items-center justify-center w-4 h-4 rounded-full text-[10px] font-bold cursor-help"
                style={{
                  color: "var(--chalk-blue)",
                  background: "var(--chalk-blue-light)",
                  border: "1px solid var(--chalk-blue)",
                }}
              >
                ?
              </span>
              <span
                className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 rounded-lg text-xs whitespace-normal w-56 text-left opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-10 pointer-events-none"
                style={{
                  fontFamily: "var(--font-crimson-pro)",
                  color: "var(--ink)",
                  background: "white",
                  border: "1px solid var(--paper-grid)",
                  boxShadow: "2px 2px 0 rgba(0,0,0,0.05)",
                }}
              >
                Single (S), Double (D), Complex (C), Double Complex (Z). LAPACK uses prefixes: e.g. DGESV = double-precision general solver.
              </span>
            </span>
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
