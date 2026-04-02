/**
 * ProgressRing Component
 *
 * An animated SVG circular progress ring for TCRTE dimension scores.
 * Fills from 0 to `score` on mount with a smooth ease-out animation.
 */

import { useEffect, useRef } from 'react';

interface ProgressRingProps {
  /** Score from 0–100 */
  score: number;
  /** Stroke color */
  color: string;
  /** Ring size in px (default 52) */
  size?: number;
  /** Stroke width (default 4) */
  strokeWidth?: number;
  /** Center label - defaults to score number */
  label?: string;
  /** Sub-label below the score */
  sublabel?: string;
  /** Delay for staggered animation (seconds) */
  delay?: number;
}

export function ProgressRing({
  score,
  color,
  size = 52,
  strokeWidth = 4,
  label,
  sublabel,
  delay = 0,
}: ProgressRingProps) {
  const progressRef = useRef<SVGCircleElement>(null);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  useEffect(() => {
    const el = progressRef.current;
    if (!el) return;

    // Start fully undrawn
    el.style.strokeDashoffset = String(circumference);
    el.style.transition = 'none';

    const timeout = setTimeout(() => {
      el.style.transition = `stroke-dashoffset 0.9s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${delay}s`;
      el.style.strokeDashoffset = String(offset);
    }, 60);

    return () => clearTimeout(timeout);
  }, [score, circumference, offset, delay]);

  const textSize = size < 50 ? '10px' : '13px';
  const sublabelSize = '8px';

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ transform: 'rotate(-90deg)' }}
        >
          {/* Track ring */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--border)"
            strokeWidth={strokeWidth}
          />
          {/* Progress ring */}
          <circle
            ref={progressRef}
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={circumference}
          />
        </svg>

        {/* Center score label */}
        <div
          className="absolute inset-0 flex items-center justify-center"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          <span
            style={{
              fontSize: textSize,
              fontWeight: 800,
              color,
              lineHeight: 1,
            }}
          >
            {label ?? score}
          </span>
        </div>
      </div>

      {sublabel && (
        <span
          style={{
            fontSize: sublabelSize,
            fontWeight: 700,
            color: 'var(--text-tertiary)',
            letterSpacing: '0.5px',
            textTransform: 'uppercase',
            textAlign: 'center',
          }}
        >
          {sublabel}
        </span>
      )}
    </div>
  );
}
