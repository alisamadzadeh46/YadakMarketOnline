"use client";
// Global form validation UX: intercepts the browser's native HTML5 validation
// bubbles on EVERY form (login, register, KYC, checkout, contact, ...) and
// replaces them with styled Persian inline errors. Zero per-form wiring.
import { useEffect } from "react";

function messageFor(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): string {
  // A field can carry its own message via data-error.
  const custom = el.getAttribute("data-error");
  const v = (el as HTMLInputElement).validity;
  if (v.valueMissing) return "پر کردن این فیلد الزامی است.";
  if (custom) return custom;
  if (v.typeMismatch && (el as HTMLInputElement).type === "email") return "یک ایمیل معتبر وارد کنید.";
  if (v.typeMismatch && (el as HTMLInputElement).type === "url") return "یک آدرس اینترنتی معتبر وارد کنید.";
  if (v.patternMismatch) return "فرمت وارد شده صحیح نیست.";
  if (v.tooShort) return `حداقل ${(el as HTMLInputElement).minLength} کاراکتر وارد کنید.`;
  if (v.tooLong) return `حداکثر ${(el as HTMLInputElement).maxLength} کاراکتر مجاز است.`;
  if (v.rangeUnderflow) return `مقدار نباید کمتر از ${(el as HTMLInputElement).min} باشد.`;
  if (v.rangeOverflow) return `مقدار نباید بیشتر از ${(el as HTMLInputElement).max} باشد.`;
  if (v.badInput) return "مقدار وارد شده معتبر نیست.";
  return "مقدار این فیلد را بررسی کنید.";
}

function showError(el: Element) {
  const field = el as HTMLInputElement;
  field.classList.add("invalid");
  const holder = field.closest(".field") || field.parentElement;
  if (!holder) return;
  let err = holder.querySelector<HTMLElement>(".field-err");
  if (!err) {
    err = document.createElement("div");
    err.className = "field-err";
    holder.appendChild(err);
  }
  err.textContent = messageFor(field);
}

function clearError(el: Element) {
  const field = el as HTMLInputElement;
  field.classList.remove("invalid");
  const holder = field.closest(".field") || field.parentElement;
  holder?.querySelector(".field-err")?.remove();
}

export default function FormValidator() {
  useEffect(() => {
    // `invalid` fires per-field when a submit fails native validation.
    const onInvalid = (e: Event) => {
      e.preventDefault(); // suppress the browser's default bubble
      showError(e.target as Element);
      // Focus the first invalid field of the form.
      const form = (e.target as HTMLInputElement).form;
      const first = form?.querySelector(":invalid") as HTMLElement | null;
      first?.focus?.();
    };
    // Live re-validation: the moment the user fixes the value, the error goes away.
    const onInput = (e: Event) => {
      const el = e.target as HTMLInputElement;
      if (el.classList?.contains("invalid") && el.checkValidity?.()) clearError(el);
    };
    document.addEventListener("invalid", onInvalid, true);
    document.addEventListener("input", onInput, true);
    document.addEventListener("change", onInput, true);
    return () => {
      document.removeEventListener("invalid", onInvalid, true);
      document.removeEventListener("input", onInput, true);
      document.removeEventListener("change", onInput, true);
    };
  }, []);
  return null;
}
