interface LogoProps {
  iconOnly?: boolean;
  showTld?: boolean;
  invert?: boolean;
  className?: string;
  /** Pixel size of the icon mark (default 32) */
  size?: number;
  /** Pixel font-size of the wordmark (defaults to size * 0.55) */
  wordmarkSize?: number;
}

export default function Logo({
  iconOnly = false,
  showTld = true,
  invert = false,
  className = '',
  size = 32,
  wordmarkSize,
}: LogoProps) {
  const fs = wordmarkSize ?? size * 0.55;
  // PNG has built-in transparent padding on the right — pull the wordmark in to compensate
  const wordmarkLeftMargin = -size * 0.18;
  return (
    <span className={`inline-flex items-center ${className}`}>
      <LogoMark size={size} />
      {!iconOnly && (
        <span
          className="font-display font-extrabold tracking-tight leading-none"
          style={{ fontSize: `${fs}px`, marginLeft: `${wordmarkLeftMargin}px` }}
        >
          <span className={invert ? 'text-white' : 'text-brand-navy'}>Only</span>
          <span className="text-brand-500">OffMarkets</span>
          {showTld && (
            <span className={invert ? 'text-white/70' : 'text-brand-navy'}>.com</span>
          )}
        </span>
      )}
    </span>
  );
}

export function LogoMark({ size = 32, className = '' }: { size?: number; className?: string }) {
  return (
    <img
      src="/logo.png"
      alt="OnlyOffMarkets"
      width={size}
      height={size}
      className={`object-contain ${className}`}
      style={{ width: size, height: size }}
    />
  );
}
