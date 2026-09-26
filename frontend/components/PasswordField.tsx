"use client";
// A password box with a show/hide toggle.
//
// Typing a password blind is worst exactly where it matters most: on register
// and on the reset pages the value has to be typed correctly with no way to
// check it, and a mistyped 9-character password fails at submit with no clue
// which character went wrong.
import { useState } from "react";

export default function PasswordField({
  value,
  onChange,
  minLength,
  required,
  autoComplete,
  dataError,
  disabled,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  minLength?: number;
  required?: boolean;
  autoComplete?: string;
  dataError?: string;
  disabled?: boolean;
  id?: string;
}) {
  const [shown, setShown] = useState(false);

  return (
    <div className="pwfield">
      <input
        id={id}
        className="inp"
        type={shown ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        minLength={minLength}
        required={required}
        autoComplete={autoComplete}
        data-error={dataError}
        disabled={disabled}
      />
      {/* type=button, or it submits the form on every peek. */}
      <button
        type="button"
        className="pwtoggle"
        onClick={() => setShown((v) => !v)}
        disabled={disabled}
        aria-label={shown ? "پنهان کردن رمز عبور" : "نمایش رمز عبور"}
        aria-pressed={shown}
        title={shown ? "پنهان کردن رمز" : "نمایش رمز"}
      >
        {shown ? (
          // eye-off: the slash says "hide", so the icon shows what the click does
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
            <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c7 0 10 8 10 8a18.5 18.5 0 0 1-2.16 3.19M6.61 6.61A18.6 18.6 0 0 0 2 12s3 8 10 8a9.7 9.7 0 0 0 5.39-1.61" />
            <path d="m2 2 20 20" />
          </svg>
        ) : (
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 12s3-8 10-8 10 8 10 8-3 8-10 8-10-8-10-8Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        )}
      </button>
    </div>
  );
}
