import { useEffect, useState } from 'react';

interface Props {
  /** 0-100 */
  score: number;
  /** Stroke + text color */
  hex: string;
  /** Pixel size of the ring (default 112) */
  size?: number;
  /** Stroke width as a viewBox-relative number (default 3.5) */
  stroke?: number;
  /** Optional label rendered under the score (e.g. "/100") */
  unit?: string;
  /** When true, doesn't animate on mount — useful for static export */
  staticRender?: boolean;
}

/** Animated circular gauge used for Deal score, ADU potential, and any
 *  future 0-100 metric. Pulls all the SVG ring + dasharray-tween logic
 *  out of individual page components. */
export default function ScoreGauge({
  score,
  hex,
  size = 112,
  stroke = 3.5,
  unit = '/100',
  staticRender = false,
}: Props) {
  const [shown, setShown] = useState(staticRender ? score : 0);

  useEffect(() => {
    if (staticRender) {
      setShown(score);
      return;
    }
    const id = requestAnimationFrame(() => setShown(score));
    return () => cancelAnimationFrame(id);
  }, [score, staticRender]);

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox="0 0 36 36" className="absolute inset-0 -rotate-90">
        <circle
          cx="18"
          cy="18"
          r="15.9"
          fill="none"
          stroke="rgb(241,245,249)"
          strokeWidth={stroke}
        />
        <circle
          cx="18"
          cy="18"
          r="15.9"
          fill="none"
          strokeWidth={stroke}
          strokeLinecap="round"
          stroke={hex}
          style={{
            strokeDasharray: `${shown} 100`,
            transition: 'stroke-dasharray 900ms cubic-bezier(0.16, 1, 0.3, 1)',
            filter: `drop-shadow(0 0 6px ${hex}40)`,
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display font-extrabold tabular-nums leading-none"
          style={{
            color: hex,
            fontSize: Math.round(size * 0.28),
          }}
        >
          {score}
        </span>
        {unit && (
          <span
            className="text-slate-400 uppercase tracking-wider mt-0.5"
            style={{ fontSize: Math.round(size * 0.085), letterSpacing: '0.08em' }}
          >
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}
