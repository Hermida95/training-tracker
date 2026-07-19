// Iconos de línea propios (stroke fino, esquinas redondeadas) en lugar de
// emojis: mantienen el tono nórdico/minimalista y heredan currentColor,
// así que se tiñen solos con el estado (activo, bronce, apagado...).

interface IconProps {
  size?: number;
  strokeWidth?: number;
}

function base(size: number) {
  return {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
}

export function SunIcon({ size = 22, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M18.7 5.3l-1.6 1.6M6.9 17.1l-1.6 1.6" />
    </svg>
  );
}

export function BarbellIcon({ size = 22, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M8.5 12h7" />
      <rect x="5" y="8" width="2.4" height="8" rx="1" />
      <rect x="16.6" y="8" width="2.4" height="8" rx="1" />
      <path d="M2.5 10v4M21.5 10v4" />
    </svg>
  );
}

export function TrendIcon({ size = 22, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M3.5 17.5l5-5 3.5 3 8-8.5" />
      <path d="M15.5 7h4.5v4.5" />
    </svg>
  );
}

export function SlidersIcon({ size = 22, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M4 7h16M4 12h16M4 17h16" />
      <circle cx="9" cy="7" r="1.9" fill="var(--bg-elevated)" />
      <circle cx="15" cy="12" r="1.9" fill="var(--bg-elevated)" />
      <circle cx="7" cy="17" r="1.9" fill="var(--bg-elevated)" />
    </svg>
  );
}

export function FlameIcon({ size = 14, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M12 21c3.6 0 6-2.3 6-5.6 0-2.6-1.6-4.4-3-6.1-1.2-1.5-2.3-2.9-2.6-4.8-.1-.6-.8-.8-1.2-.4C9.6 5.7 8.6 7.6 8.6 9.6c-.7-.5-1.2-1.2-1.5-2-.2-.5-.9-.6-1.2-.1C5.2 8.8 4.4 10.7 4.4 12.7 4.4 17 7.4 21 12 21z" />
    </svg>
  );
}

export function StarIcon({ size = 24, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M12 3.2l2.6 5.3 5.8.8-4.2 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8L3.6 9.3l5.8-.8L12 3.2z" />
    </svg>
  );
}

export function CircleCheckIcon({ size = 24, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.5 12.2l2.4 2.4 4.6-4.8" />
    </svg>
  );
}

export function CircleHalfIcon({ size = 24, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <circle cx="12" cy="12" r="8.5" />
      {/* mitad rellena: el día va a medias */}
      <path d="M12 3.5a8.5 8.5 0 010 17z" fill="currentColor" stroke="none" opacity="0.55" />
    </svg>
  );
}

export function CircleIcon({ size = 24, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <circle cx="12" cy="12" r="8.5" />
    </svg>
  );
}

export function LeafIcon({ size = 24, strokeWidth = 1.6 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M5 19C5 10 10 5 19.5 4.5 20 14 15 19 6.5 19H5z" />
      <path d="M5 19c2.5-5.5 6-9 10.5-11" />
    </svg>
  );
}

export function CheckIcon({ size = 22, strokeWidth = 2 }: IconProps) {
  return (
    <svg {...base(size)} strokeWidth={strokeWidth}>
      <path d="M4.5 12.5l5 5 10-11" />
    </svg>
  );
}
