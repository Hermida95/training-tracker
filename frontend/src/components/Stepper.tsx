interface StepperProps {
  value: number | null;
  onChange: (value: number) => void;
  step?: number;
  suffix?: string;
  min?: number;
}

/** Control +/- para registrar peso o reps en 2 toques, sin teclado. */
export function Stepper({ value, onChange, step = 1, suffix = "", min = 0 }: StepperProps) {
  const current = value ?? 0;
  const clamp = (n: number) => Math.max(min, Math.round(n * 100) / 100);
  // Miles con separador local (10500 -> "10.500"): más legible de un vistazo.
  const shown = value === null ? "–" : value.toLocaleString("es-ES");

  return (
    <div className="stepper">
      <button type="button" aria-label="Restar" onClick={() => onChange(clamp(current - step))}>
        −
      </button>
      <output>
        <span className="stepper-value">{shown}</span>
        {/* La unidad va en su propia línea: "10.500 pasos" en una sola línea
            no cabe en móviles estrechos y se truncaba a "105…". */}
        {value !== null && suffix.trim() && (
          <span className="stepper-unit">{suffix.trim()}</span>
        )}
      </output>
      <button type="button" aria-label="Sumar" onClick={() => onChange(clamp(current + step))}>
        +
      </button>
    </div>
  );
}
