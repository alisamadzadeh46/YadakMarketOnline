"use client";
// Supplier-panel attention grabber: polls every 60s; while orders are waiting
// for confirmation it beeps (WebAudio — no sound file needed), shows a toast
// and blinks the tab title until the supplier confirms them.
import { useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";

function beep() {
  try {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext;
    const ctx = new Ctx();
    // Two-tone "ding-dong" chime.
    [[880, 0], [660, 0.18]].forEach(([freq, at]) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.value = freq as number;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime + (at as number));
      gain.gain.exponentialRampToValueAtTime(0.28, ctx.currentTime + (at as number) + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + (at as number) + 0.45);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime + (at as number));
      osc.stop(ctx.currentTime + (at as number) + 0.5);
    });
    setTimeout(() => ctx.close(), 1200);
  } catch { /* audio blocked until first user gesture — fine */ }
}

export default function NewOrderAlert() {
  const baseTitle = useRef<string>("");

  useEffect(() => {
    baseTitle.current = document.title;
    let blink: ReturnType<typeof setInterval> | undefined;

    const check = async () => {
      try {
        const d = await api.get("/suppliers/dashboard/");
        const pending = d.orders_pending_receipt || 0;
        clearInterval(blink);
        if (pending > 0) {
          beep();
          toast(`🔔 شما ${toFa(pending)} سفارش جدید در انتظار تایید دارید!`);
          let flip = false;
          blink = setInterval(() => {
            document.title = flip ? `🔔 (${pending}) سفارش جدید!` : baseTitle.current;
            flip = !flip;
          }, 1200);
        } else {
          document.title = baseTitle.current;
        }
      } catch { /* ignore transient errors */ }
    };

    check();
    const poll = setInterval(check, 60_000); // repeat every minute until confirmed
    return () => { clearInterval(poll); clearInterval(blink); document.title = baseTitle.current; };
  }, []);

  return null;
}
