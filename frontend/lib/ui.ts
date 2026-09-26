"use client";
import { api } from "./api";
import { hasSession } from "./api";
import { errorMessage } from "@/lib/api";

// Fire a transient toast from anywhere on the client.
export function toast(message: string) {
  if (typeof window !== "undefined")
    window.dispatchEvent(new CustomEvent("ym-toast", { detail: message }));
}

// ---- Guest cart -------------------------------------------------------------
// The real cart lives server-side and needs auth, so a signed-out shopper's
// picks are parked in localStorage and merged into their account right after
// login (see mergeGuestCart, called from the auth context).
const GUEST_CART_KEY = "ym_guest_cart";
type GuestLine = { product: number; quantity: number; color?: number | null };

function readGuestCart(): GuestLine[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(GUEST_CART_KEY);
    return raw ? (JSON.parse(raw) as GuestLine[]) : [];
  } catch {
    return [];
  }
}

function writeGuestCart(lines: GuestLine[]) {
  try {
    window.localStorage.setItem(GUEST_CART_KEY, JSON.stringify(lines));
  } catch {
    /* storage full or blocked — the redirect to login still works */
  }
}

export function guestCartCount(): number {
  return readGuestCart().reduce((n, l) => n + l.quantity, 0);
}

/** Push any parked guest lines into the server cart, then clear them. */
export async function mergeGuestCart(): Promise<boolean> {
  const lines = readGuestCart();
  if (!lines.length) return false;
  let merged = 0;
  for (const line of lines) {
    try {
      await api.post("/orders/cart/", line);
      merged += 1;
    } catch {
      // A line that is now out of stock / unpriced is skipped rather than
      // blocking the rest of the merge.
    }
  }
  try {
    window.localStorage.removeItem(GUEST_CART_KEY);
  } catch { /* ignore */ }
  if (merged) {
    toast("کالاهای سبد خرید شما بازیابی شد ✓");
    window.dispatchEvent(new Event("ym-cart-changed"));
  }
  return merged > 0;
}

// Add a product (optionally one specific colour) to the cart. Signed out, it
// is remembered locally and restored automatically after login instead of
// being silently lost.
export async function addToCart(
  productId: number,
  quantity: number,
  colorId?: number | null
) {
  if (!hasSession()) {
    const lines = readGuestCart();
    // A different colour of the same product is its own line — matches the
    // server cart, which keys on (product, color) rather than product alone.
    const existing = lines.find(
      (l) => l.product === productId && (l.color ?? null) === (colorId ?? null)
    );
    if (existing) existing.quantity += quantity;
    else lines.push({ product: productId, quantity, color: colorId ?? null });
    writeGuestCart(lines);
    window.dispatchEvent(new Event("ym-cart-changed"));
    toast("به سبد افزوده شد — برای تکمیل خرید وارد شوید");
    setTimeout(() => (window.location.href = "/login"), 1100);
    return false;
  }
  try {
    await api.post("/orders/cart/", { product: productId, quantity, color: colorId ?? null });
    toast("به سبد خرید افزوده شد ✓");
    window.dispatchEvent(new Event("ym-cart-changed"));
    return true;
  } catch (e) {
    toast(errorMessage(e, "خطا در افزودن به سبد"));
    return false;
  }
}

/** A same-site path to continue to after sign-in, or "/" when unsafe.
 *  Only a single leading slash is accepted; "//host" and "/\\host" would be
 *  read by the browser as another site (an open redirect). */
export function safeNextPath(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return "/";
  return next;
}
