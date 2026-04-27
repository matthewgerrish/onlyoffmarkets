interface Props {
  frontHtml: string;
  backHtml: string;
  size?: '4x6' | '6x9' | '6x11';
}

/** Render front + back of a postcard side-by-side using sandboxed iframes. */
export default function PostcardPreview({ frontHtml, backHtml, size = '4x6' }: Props) {
  const dims = (() => {
    switch (size) {
      case '6x9':  return { w: 360, h: 240 };
      case '6x11': return { w: 440, h: 240 };
      default:     return { w: 360, h: 240 };
    }
  })();

  return (
    <div className="grid sm:grid-cols-2 gap-4">
      {[
        { label: 'Front', html: frontHtml },
        { label: 'Back', html: backHtml },
      ].map((side) => (
        <div key={side.label}>
          <div className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-1.5">{side.label}</div>
          <div
            className="border border-slate-200 rounded-xl overflow-hidden bg-white shadow-sm"
            style={{ width: dims.w, height: dims.h, maxWidth: '100%' }}
          >
            <iframe
              title={`postcard-${side.label}`}
              srcDoc={side.html}
              sandbox=""
              className="w-full h-full border-0"
              style={{ width: '100%', height: '100%' }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
