"use client";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";

export default function Toaster() {
  const [msg, setMsg] = useState<string | null>(null);
  const { refreshCart } = useAuth();

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const onToast = (e: Event) => {
      setMsg((e as CustomEvent).detail);
      clearTimeout(timer);
      timer = setTimeout(() => setMsg(null), 2400);
    };
    const onCart = () => refreshCart();
    window.addEventListener("ym-toast", onToast);
    window.addEventListener("ym-cart-changed", onCart);
    return () => {
      window.removeEventListener("ym-toast", onToast);
      window.removeEventListener("ym-cart-changed", onCart);
      clearTimeout(timer);
    };
  }, [refreshCart]);

  if (!msg) return null;
  return <div className="toast">{msg}</div>;
}
