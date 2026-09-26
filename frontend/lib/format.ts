// Persian-digit and currency helpers used across the UI.
const FA = "۰۱۲۳۴۵۶۷۸۹";
const AR = "٠١٢٣٤٥٦٧٨٩";

export const toFa = (n: number | string): string =>
  String(n).replace(/\d/g, (d) => FA[+d]);

export const money = (n: number): string =>
  toFa((n ?? 0).toLocaleString("en-US"));

/** Anything the user typed -> plain ASCII digits, nothing else.
 *  A Persian keyboard emits ۰-۹ and an Arabic one ٠-٩; both look like numbers
 *  to the reader and like garbage to parseInt and to the API. */
export const digitsOnly = (s: unknown): string =>
  // Coerced, not typed as string: these values come back from DRF as numbers
  // ("stock": 5) and as Decimal strings ("price": "10000.00"), and calling
  // .replace on a number threw, which took the whole products page down.
  String(s ?? "")
    .replace(/[۰-۹]/g, (d) => String(FA.indexOf(d)))
    .replace(/[٠-٩]/g, (d) => String(AR.indexOf(d)))
    .replace(/\D/g, "");

/** Raw digits -> Persian digits grouped in threes: "1870000" → «۱,۸۷۰,۰۰۰».
 *  Same comma money() uses, so a typed price reads like a displayed one. */
export const faGroup = (raw: unknown): string => {
  const s = String(raw ?? "");
  return s ? toFa(s.replace(/\B(?=(\d{3})+(?!\d))/g, ",")) : "";
};

/** Jalali date + 24h clock (e.g. 14 Mordad 1405, 12:38) — for receipts. */
export const faDateTime = (iso?: string): string => {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const day = new Intl.DateTimeFormat("fa-IR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(d);
    const time = new Intl.DateTimeFormat("fa-IR", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(d);
    return `${day} ساعت ${time}`;
  } catch {
    return iso;
  }
};

export const faDate = (iso?: string): string => {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("fa-IR", {
      year: "numeric",
      month: "long",
      day: "numeric",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
};

/** Average rating with at most one decimal, in Persian digits: "4.50" -> «۴.۵». */
export function rating(value: number | string | null | undefined): string {
  const number = Number(value);
  return Number.isFinite(number) ? toFa(String(Math.round(number * 10) / 10)) : "";
}
