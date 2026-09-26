"use client";
// Jalali (Solar Hijri) date+time picker — no external deps. Emits an ISO string.
// Conversion uses the standard jalaali algorithm (pure arithmetic).
import { useMemo } from "react";
import NiceSelect from "./NiceSelect";
import { toFa } from "@/lib/format";

/* ---- jalaali <-> gregorian (algorithmic, no CDN) ---- */
function div(a: number, b: number) { return ~~(a / b); }
function mod(a: number, b: number) { return a - ~~(a / b) * b; }
function jalCal(jy: number) {
  const breaks = [-61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210, 1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178];
  const bl = breaks.length, gy = jy + 621;
  let leapJ = -14, jp = breaks[0], jump = 0;
  for (let i = 1; i < bl; i += 1) {
    const jm = breaks[i]; jump = jm - jp;
    if (jy < jm) break;
    leapJ = leapJ + div(jump, 33) * 8 + div(mod(jump, 33), 4);
    jp = jm;
  }
  let n = jy - jp;
  leapJ = leapJ + div(n, 33) * 8 + div(mod(n, 33) + 3, 4);
  if (mod(jump, 33) === 4 && jump - n === 4) leapJ += 1;
  const leapG = div(gy, 4) - div((div(gy, 100) + 1) * 3, 4) - 150;
  const march = 20 + leapJ - leapG;
  if (jump - n < 6) n = n - jump + div(jump + 4, 33) * 33;
  let leap = mod(mod(n + 1, 33) - 1, 4);
  if (leap === -1) leap = 4;
  return { leap, gy, march };
}
function g2d(gy: number, gm: number, gd: number) {
  let d = div((gy + div(gm - 8, 6) + 100100) * 1461, 4) + div(153 * mod(gm + 9, 12) + 2, 5) + gd - 34840408;
  d = d - div(div(gy + 100100 + div(gm - 8, 6), 100) * 3, 4) + 752;
  return d;
}
function d2g(jdn: number) {
  let j = 4 * jdn + 139361631;
  j = j + div(div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908;
  const i = div(mod(j, 1461), 4) * 5 + 308;
  const gd = div(mod(i, 153), 5) + 1;
  const gm = mod(div(i, 153), 12) + 1;
  const gy = div(j, 1461) - 100100 + div(8 - gm, 6);
  return { gy, gm, gd };
}
function j2d(jy: number, jm: number, jd: number) {
  const r = jalCal(jy);
  return g2d(r.gy, 3, r.march) + (jm - 1) * 31 - div(jm, 7) * (jm - 7) + jd - 1;
}
function d2j(jdn: number) {
  const gy = d2g(jdn).gy;
  let jy = gy - 621;
  const r = jalCal(jy);
  const jdn1f = g2d(gy, 3, r.march);
  let jd, jm, k = jdn - jdn1f;
  if (k >= 0) {
    if (k <= 185) { jm = 1 + div(k, 31); jd = mod(k, 31) + 1; return { jy, jm, jd }; }
    k -= 186;
  } else {
    jy -= 1; k += 179;
    if (jalCal(jy).leap === 1) k += 1;
  }
  jm = 7 + div(k, 30); jd = mod(k, 30) + 1;
  return { jy, jm, jd };
}
export function jalaliToIso(jy: number, jm: number, jd: number, hh = 0, mi = 0): string {
  const { gy, gm, gd } = d2g(j2d(jy, jm, jd));
  const dt = new Date(gy, gm - 1, gd, hh, mi);
  return dt.toISOString();
}
export function isoToJalali(iso?: string) {
  const d = iso ? new Date(iso) : new Date();
  const j = d2j(g2d(d.getFullYear(), d.getMonth() + 1, d.getDate()));
  return { ...j, hh: d.getHours(), mi: d.getMinutes() };
}
/* ---------------------------------------------------- */

const MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];

export default function JalaliPicker({
  value,
  onChange,
  withTime = true,
}: {
  value?: string | null;          // ISO string
  onChange: (iso: string) => void;
  withTime?: boolean;
}) {
  const j = useMemo(() => isoToJalali(value || undefined), [value]);
  const nowJy = isoToJalali().jy;

  const set = (patch: Partial<typeof j>) => {
    const next = { ...j, ...patch };
    onChange(jalaliToIso(next.jy, next.jm, Math.min(next.jd, 31), next.hh, next.mi));
  };

  const opts = (arr: (number | string)[], labelFn?: (v: any) => string) =>
    arr.map((v, i) => ({ value: String(typeof v === "number" ? v : i + 1), label: labelFn ? labelFn(v) : toFa(v) }));

  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
      <NiceSelect style={{ minWidth: 78 }} value={String(j.jd)} onChange={(v) => set({ jd: +v })}
        options={opts(Array.from({ length: 31 }, (_, i) => i + 1))} />
      <NiceSelect style={{ minWidth: 110 }} value={String(j.jm)} onChange={(v) => set({ jm: +v })}
        options={MONTHS.map((m, i) => ({ value: String(i + 1), label: m }))} />
      <NiceSelect style={{ minWidth: 88 }} value={String(j.jy)} onChange={(v) => set({ jy: +v })}
        options={opts(Array.from({ length: 6 }, (_, i) => nowJy + i))} />
      {withTime && (
        <>
          <NiceSelect style={{ minWidth: 76 }} value={String(j.hh)} onChange={(v) => set({ hh: +v })}
            options={opts(Array.from({ length: 24 }, (_, i) => i), (v) => `${toFa(String(v).padStart(2, "0"))} ساعت`)} />
          <NiceSelect style={{ minWidth: 76 }} value={String(j.mi - (j.mi % 5))} onChange={(v) => set({ mi: +v })}
            options={opts(Array.from({ length: 12 }, (_, i) => i * 5), (v) => `${toFa(String(v).padStart(2, "0"))} دقیقه`)} />
        </>
      )}
    </div>
  );
}
