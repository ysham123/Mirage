"use client";

interface ConfidenceRingProps {
  label: string;
  value: number;
}

export function ConfidenceRing({ label, value }: ConfidenceRingProps) {
  const degrees = Math.round(value * 360);

  return (
    <div className="rounded-[1.4rem] border border-white/10 bg-black/20 p-4">
      <div
        className="relative mx-auto flex size-28 items-center justify-center rounded-full"
        style={{
          background: `conic-gradient(rgba(111,231,255,.9) 0deg ${degrees}deg, rgba(255,255,255,.06) ${degrees}deg 360deg)`,
        }}
      >
        <div className="absolute inset-[8px] rounded-full bg-[rgba(4,8,12,.94)]" />
        <div className="relative text-center">
          <p className="text-2xl font-semibold tracking-[-0.04em] text-white">{Math.round(value * 100)}%</p>
          <p className="text-[0.62rem] uppercase tracking-[0.24em] text-[var(--text-muted)]">{label}</p>
        </div>
      </div>
    </div>
  );
}
