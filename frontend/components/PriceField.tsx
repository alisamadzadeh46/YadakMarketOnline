"use client";
// A price box that shows Persian digits grouped in threes («۱,۸۷۰,۰۰۰») as you
// type, while the raw ASCII digits stay in state for the API.
//
// This exists because <input type="number"> cannot do any of it: it refuses a
// value containing separators or Persian digits, and it paints the two spinner
// arrows that have no place in this design. A text field with inputMode
// "numeric" still brings up the number pad on a phone.
import { useRef } from "react";
import { digitsOnly, faGroup } from "@/lib/format";

export default function PriceField({
  value,
  onChange,
  placeholder,
  required,
  className = "inp",
  style,
}: {
  value: string | number | null | undefined;
  onChange: (raw: string) => void;
  placeholder?: string;
  required?: boolean;
  className?: string;
  style?: React.CSSProperties;
}) {
  const ref = useRef<HTMLInputElement>(null);

  // What to paint. DRF hands prices back as Decimal strings ("10000.00") and
  // counts as numbers, so normalise for DISPLAY only: keep the part before the
  // decimal point (Toman has no sub-unit) and drop anything that is not a
  // digit. State itself is untouched until the user actually types, so opening
  // a product and saving it without touching the price cannot alter it.
  const shownRaw = digitsOnly(String(value ?? "").split(".")[0]);

  const handle = (e: React.ChangeEvent<HTMLInputElement>) => {
    const el = e.target;
    // How many digits sit before the caret — the one anchor that survives
    // reformatting, since the commas around them are about to move.
    const before = digitsOnly(el.value.slice(0, el.selectionStart ?? 0)).length;
    const raw = digitsOnly(el.value);
    onChange(raw);

    // Put the caret back after that same digit. Without this, every inserted
    // comma shoves it to the end and correcting a digit mid-number is
    // impossible — you would have to clear the field and start over.
    requestAnimationFrame(() => {
      const node = ref.current;
      if (!node) return;
      const shown = faGroup(raw);
      let seen = 0;
      let pos = before === 0 ? 0 : shown.length;
      for (let i = 0; i < shown.length; i++) {
        if (shown[i] !== ",") seen++;
        if (seen === before) {
          pos = i + 1;
          break;
        }
      }
      node.setSelectionRange(pos, pos);
    });
  };

  return (
    <input
      ref={ref}
      className={className}
      type="text"
      inputMode="numeric"
      autoComplete="off"
      required={required}
      placeholder={placeholder}
      value={faGroup(shownRaw)}
      onChange={handle}
      style={style}
    />
  );
}
