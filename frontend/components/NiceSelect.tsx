"use client";
// Custom dropdown that renders options with the site font (native <select>
// option lists are OS-drawn and ignore our webfont).
import { useEffect, useRef, useState } from "react";

export type Option = { value: string; label: string };

export default function NiceSelect({
  value,
  options,
  onChange,
  style,
}: {
  value: string;
  options: Option[];
  onChange: (v: string) => void;
  style?: React.CSSProperties;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const current = options.find((o) => o.value === value);

  return (
    <div className={`nsel ${open ? "open" : ""}`} ref={ref} style={style}>
      <button type="button" onClick={() => setOpen(!open)}>
        <span>{current?.label ?? "انتخاب…"}</span>
        <svg className="chev" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M6 9l6 6 6-6" /></svg>
      </button>
      {open && (
        <div className="menu">
          {options.map((o) => (
            <button type="button" key={o.value} className={o.value === value ? "on" : ""}
              onClick={() => { onChange(o.value); setOpen(false); }}>
              {o.label}
              {o.value === value && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M5 12l5 5L20 7" /></svg>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
