import { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { Copy, Download } from 'lucide-react';

interface Props {
  initialUrl?: string;
  onChange?: (url: string) => void;
  size?: number;
}

/** Lightweight QR-code maker. Type a URL/phone, get a scannable code.
 *  The SVG can be downloaded or copied as a data URL for embedding into postcards. */
export default function QRMaker({ initialUrl = '', onChange, size = 160 }: Props) {
  const [url, setUrl] = useState(initialUrl);
  const [copied, setCopied] = useState(false);

  const setValue = (v: string) => {
    setUrl(v);
    onChange?.(v);
  };

  const downloadSvg = () => {
    const svg = document.getElementById('qrmaker-svg');
    if (!svg) return;
    const data = new XMLSerializer().serializeToString(svg);
    const blob = new Blob([data], { type: 'image/svg+xml' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `qr-${url.replace(/[^a-z0-9]/gi, '_').slice(0, 20) || 'code'}.svg`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const copyDataUri = async () => {
    const svg = document.getElementById('qrmaker-svg');
    if (!svg) return;
    const data = new XMLSerializer().serializeToString(svg);
    const dataUri = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(data)));
    await navigator.clipboard.writeText(dataUri);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="card p-5">
      <div className="text-xs uppercase tracking-wider font-bold text-slate-400 mb-3">QR Code</div>
      <div className="flex gap-5 items-start flex-wrap">
        <div className="bg-white border border-slate-200 rounded-xl p-3 shrink-0">
          {url ? (
            <QRCodeSVG
              id="qrmaker-svg"
              value={url}
              size={size}
              level="M"
              fgColor="#0f1f3d"
              bgColor="#ffffff"
              marginSize={1}
            />
          ) : (
            <div
              className="bg-slate-50 border border-dashed border-slate-200 rounded text-slate-400 text-xs flex items-center justify-center text-center px-2"
              style={{ width: size, height: size }}
            >
              Enter URL or phone to generate
            </div>
          )}
        </div>
        <div className="flex-1 min-w-[200px] space-y-3">
          <div>
            <label className="block text-xs text-slate-600 font-semibold mb-1">Destination</label>
            <input
              className="input w-full"
              placeholder="https://onlyoffmarkets.com/sell or tel:+15551234567"
              value={url}
              onChange={(e) => setValue(e.target.value)}
            />
            <p className="text-[11px] text-slate-500 mt-1">
              Scanning the QR opens this URL. Use <code className="font-mono">tel:</code> for phone, <code className="font-mono">sms:</code> for text, or any URL.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={downloadSvg}
              disabled={!url}
              className="btn-outline text-xs disabled:opacity-40"
            >
              <Download className="w-3.5 h-3.5" /> SVG
            </button>
            <button
              type="button"
              onClick={copyDataUri}
              disabled={!url}
              className="btn-outline text-xs disabled:opacity-40"
            >
              <Copy className="w-3.5 h-3.5" /> {copied ? 'Copied' : 'Copy data URI'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
