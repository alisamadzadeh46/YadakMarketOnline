"use client";
// Footer newsletter signup — subscribers get an email per published post.
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";

export default function NewsletterForm() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.post("/cms/newsletter/subscribe/", { email }, { auth: false });
      toast(r.detail || "عضویت ثبت شد ✓");
      setEmail("");
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit} style={{ display: "flex", gap: 8, marginTop: 14 }}>
      <input
        type="email"
        required
        placeholder="ایمیل شما"
        dir="ltr"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        // LTR so the address itself reads correctly, right-aligned so the
        // Persian placeholder starts on the right like every other field.
        style={{ flex: 1, height: 44, borderRadius: 12, border: "1px solid rgba(255,255,255,.15)", background: "rgba(255,255,255,.06)", padding: "0 14px", color: "#fff", outline: "none", fontSize: 13, fontFamily: "inherit", textAlign: "right" }}
      />
      <button className="btn btn-orange" style={{ height: 44, padding: "0 16px" }} disabled={busy}>
        {busy ? "..." : "عضویت"}
      </button>
    </form>
  );
}
