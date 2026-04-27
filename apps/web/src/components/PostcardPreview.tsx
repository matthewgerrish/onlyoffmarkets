import { useEffect, useRef, useState } from 'react';

interface Props {
  frontHtml: string;
  backHtml: string;
  size?: '4x6' | '6x9' | '6x11';
}

const NATURAL: Record<NonNullable<Props['size']>, { w: number; h: number }> = {
  '4x6':  { w: 576, h: 384 },
  '6x9':  { w: 864, h: 576 },
  '6x11': { w: 1056, h: 576 },
};

/** Render front + back of a postcard side-by-side. The HTML uses inch units
 *  (rendered at 1in = 96px), so we scale via CSS transform to fit any
 *  container width while preserving aspect ratio. */
export default function PostcardPreview({ frontHtml, backHtml, size = '4x6' }: Props) {
  return (
    <div className="grid sm:grid-cols-2 gap-4">
      <PostcardSide label="Front" html={frontHtml} natural={NATURAL[size]} />
      <PostcardSide label="Back" html={backHtml} natural={NATURAL[size]} />
    </div>
  );
}

function PostcardSide({
  label,
  html,
  natural,
}: {
  label: string;
  html: string;
  natural: { w: number; h: number };
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const compute = () => {
      const w = el.clientWidth;
      if (w > 0) setScale(Math.min(1, w / natural.w));
    };
    compute();
    const ro = new ResizeObserver(compute);
    ro.observe(el);
    return () => ro.disconnect();
  }, [natural.w]);

  return (
    <div className="min-w-0">
      <div className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-1.5">
        {label}
      </div>
      <div
        ref={wrapRef}
        className="w-full border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm"
        style={{ aspectRatio: `${natural.w} / ${natural.h}` }}
      >
        <iframe
          title={`postcard-${label}`}
          srcDoc={html}
          sandbox=""
          className="border-0"
          style={{
            width: natural.w,
            height: natural.h,
            transform: `scale(${scale})`,
            transformOrigin: 'top left',
          }}
        />
      </div>
    </div>
  );
}
