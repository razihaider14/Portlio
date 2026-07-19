interface ConfidenceBarProps {
  /** average_detector_confidence from a SkillProfile, expected in [0, 1]. */
  value: number;
  /** Defaults to "Detector confidence". Override for context, e.g. a specific skill name. */
  label?: string;
  className?: string;
}

/**
 * Renders a 0-1 confidence float as a 0-100% horizontal bar.
 *
 * Accessible per the WAI-ARIA "meter"/progress pattern: the bar itself
 * carries role="progressbar" with numeric aria-value* attributes, and an
 * aria-label so a screen reader announces something like "Detector
 * confidence: 92%" rather than just a bare percentage with no context.
 * Value is clamped defensively — the backend contract guarantees [0, 1],
 * but a bar that silently overflows past 100% on unexpected input would be
 * a worse failure mode than clamping.
 */
export function ConfidenceBar({
  value,
  label = "Detector confidence",
  className,
}: ConfidenceBarProps) {
  const clamped = Math.min(1, Math.max(0, value));
  const percent = Math.round(clamped * 100);

  return (
    <div className={className}>
      <div className="text-muted-foreground mb-1 flex items-center justify-between text-xs">
        <span>{label}</span>
        <span className="font-medium tabular-nums">{percent}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${label}: ${percent}%`}
        className="bg-muted h-2 w-full overflow-hidden rounded-full"
      >
        <div
          className="bg-primary h-full rounded-full transition-[width]"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
