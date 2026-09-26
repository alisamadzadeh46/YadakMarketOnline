"use client";
// A NiceSelect that can be searched, and whose list can be managed in place.
//
// The product form used a plain dropdown for brand/category. With hundreds of
// brands that means scrolling by eye, and adding a missing one meant leaving
// the half-filled form for another page. This keeps both jobs here: type to
// filter, and create/rename/remove an entry without navigating away.
import { useEffect, useMemo, useRef, useState } from "react";

export type Item = { id: number; name: string };

export default function SearchSelect({
  value,
  items,
  onChange,
  placeholder = "انتخاب…",
  searchPlaceholder = "جست‌وجو…",
  onCreate,
  onRename,
  onDelete,
  createLabel = "ثبت سریع",
}: {
  value: string;
  items: Item[];
  onChange: (v: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  /** Create a new entry and return it; the new value is selected on success. */
  onCreate?: (name: string) => Promise<Item | null>;
  onRename?: (id: number, name: string) => Promise<void>;
  onDelete?: (id: number) => Promise<void>;
  createLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) { setOpen(false); setQ(""); }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  useEffect(() => { if (open) searchRef.current?.focus(); }, [open]);

  const current = items.find((i) => String(i.id) === value);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((i) => i.name.toLowerCase().includes(needle));
  }, [items, q]);

  // Offer creation only for a genuinely new name, never a near-duplicate of
  // something already in the list.
  const canCreate =
    !!onCreate &&
    q.trim().length > 0 &&
    !items.some((i) => i.name.trim().toLowerCase() === q.trim().toLowerCase());

  const create = async () => {
    if (!onCreate || busy) return;
    setBusy(true);
    try {
      const made = await onCreate(q.trim());
      if (made) { onChange(String(made.id)); setOpen(false); setQ(""); }
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={`nsel ssel ${open ? "open" : ""}`} ref={ref}>
      <button type="button" onClick={() => setOpen(!open)}>
        <span>{current?.name ?? placeholder}</span>
        <svg className="chev" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M6 9l6 6 6-6" /></svg>
      </button>

      {open && (
        <div className="menu">
          <div className="ssel-search">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.2-3.2" />
            </svg>
            <input
              ref={searchRef}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder={searchPlaceholder}
              onKeyDown={(e) => {
                if (e.key === "Enter") { e.preventDefault(); if (canCreate) create(); }
                if (e.key === "Escape") { setOpen(false); setQ(""); }
              }}
            />
          </div>

          {canCreate && (
            <button type="button" className="ssel-create" onClick={create} disabled={busy}>
              <span className="ssel-plus">+</span>
              {busy ? "در حال ثبت…" : `${createLabel} «${q.trim()}»`}
            </button>
          )}

          <div className="ssel-list">
            <button type="button" className={value === "" ? "on" : ""} onClick={() => { onChange(""); setOpen(false); setQ(""); }}>
              {placeholder}
            </button>
            {filtered.map((it) => (
              <div key={it.id} className="ssel-row">
                <button
                  type="button"
                  className={String(it.id) === value ? "on" : ""}
                  onClick={() => { onChange(String(it.id)); setOpen(false); setQ(""); }}
                >
                  {it.name}
                  {String(it.id) === value && <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M5 12l5 5L20 7" /></svg>}
                </button>
                {(onRename || onDelete) && (
                  <span className="ssel-tools">
                    {onRename && (
                      <button type="button" title="ویرایش نام" onClick={async (e) => {
                        e.stopPropagation();
                        const next = window.prompt("نام جدید:", it.name);
                        if (next && next.trim() && next.trim() !== it.name) await onRename(it.id, next.trim());
                      }}>✎</button>
                    )}
                    {onDelete && (
                      <button type="button" title="حذف" className="del" onClick={async (e) => {
                        e.stopPropagation();
                        if (window.confirm(`«${it.name}» حذف شود؟`)) await onDelete(it.id);
                      }}>×</button>
                    )}
                  </span>
                )}
              </div>
            ))}
            {!filtered.length && !canCreate && (
              <div className="ssel-empty">موردی پیدا نشد.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
