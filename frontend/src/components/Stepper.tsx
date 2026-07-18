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

  return (
    <div className="stepper">
      <button type="button" aria-label="Restar" onClick={() => onChange(clamp(current - step))}>
        −
      </button>
      <output>
        {value ?? "–"}
        {value !== null && suffix}
      </output>
      <button type="button" aria-label="Sumar" onClick={() => onChange(clamp(current + step))}>
        +
      </button>
    </div>
  );
}
