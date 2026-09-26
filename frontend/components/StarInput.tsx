"use client";
// Clickable 5-star rating picker with hover preview.
import { useState } from "react";

export default function StarInput({
  value,
  onChange,
  size = 26,
}: {
  value: number;
  onChange: (v: number) => void;
  size?: number;
}) {
  const [hover, setHover] = useState(0);
  const active = hover || value;
  return (
    <div className="starpick" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          type="button"
          key={n}
          className={n <= active ? "on" : ""}
          onClick={() => onChange(n)}
          onMouseEnter={() => setHover(n)}
          aria-label={`${n} ستاره`}
        >
          <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l3 6.5 7 .9-5 4.9 1.2 7-6.2-3.4L5.8 21l1.2-7-5-4.9 7-.9z" />
          </svg>
        </button>
      ))}
    </div>
  );
}
