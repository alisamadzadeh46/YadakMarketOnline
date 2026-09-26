"use client";
// Professional article page: gradient cover, meta bar, rendered markdown-ish
// headings, share actions, and related posts.
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa, faDate } from "@/lib/format";
import { SITE } from "@/lib/site";

// Minimal renderer: "## title" becomes an h2, blank lines split paragraphs.
function renderBody(body: string) {
  return body.split(/\n{2,}/).map((block, i) => {
    const t = block.trim();
    if (t.startsWith("###")) return <h3 key={i} style={{ fontSize: 18, fontWeight: 800, margin: "26px 0 10px" }}>{t.replace(/^#+\s*/, "")}</h3>;
    if (t.startsWith("##")) return <h2 key={i} style={{ fontSize: 21, fontWeight: 800, margin: "30px 0 12px", display: "flex", gap: 10, alignItems: "center" }}><span style={{ width: 5, height: 20, borderRadius: 3, background: "linear-gradient(var(--purple),var(--orange))" }} />{t.replace(/^#+\s*/, "")}</h2>;
    return <p key={i} style={{ lineHeight: 2.2, color: "var(--ink-soft)", margin: "0 0 16px", fontSize: 15 }}>{t}</p>;
  });
}

export default function Post() {
  const params = useParams<{ slug: string }>();
  const slug = decodeURIComponent(params.slug);
  const [p, setP] = useState<any>(null);
  const [related, setRelated] = useState<any[]>([]);

  useEffect(() => {
    api.get(`/blog/posts/${encodeURIComponent(slug)}/`).then((post) => {
      setP(post);
      api.get("/blog/posts/").then((d) =>
        setRelated((d.results || d).filter((x: any) => x.slug !== post.slug).slice(0, 3))
      );
    }).catch(() => {});
  }, [slug]);

  if (!p) return <div className="center-empty">در حال بارگذاری…</div>;

  const share = async () => {
    try {
      if (navigator.share) await navigator.share({ title: p.title, url: location.href });
      else { await navigator.clipboard.writeText(location.href); toast("لینک مقاله کپی شد ✓"); }
    } catch {}
  };

  return (
    <div className="view">
      <div className="crumb"><Link href="/">خانه</Link><span>/</span><Link href="/blog">وبلاگ</Link><span>/</span><span style={{ color: "var(--ink)" }}>{p.title}</span></div>

      <article style={{ maxWidth: 800, margin: "0 auto" }}>
        {/* cover */}
        <div style={{ borderRadius: "var(--r-lg)", overflow: "hidden", position: "relative", minHeight: 240, display: "flex", alignItems: "flex-end", background: p.cover ? undefined : "radial-gradient(500px 260px at 80% 0%,rgba(255,138,61,.35),transparent),linear-gradient(130deg,var(--purple-deep),var(--purple-2))" }}>
          {p.cover && <img src={p.cover} alt={p.title} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }} />}
          <div style={{ position: "relative", padding: "70px 30px 26px", width: "100%", background: "linear-gradient(transparent, rgba(20,10,40,.75))", color: "#fff" }}>
            {p.category_name && <span className="badge" style={{ background: "rgba(255,138,61,.25)", color: "var(--orange-2)", border: "1px solid rgba(255,138,61,.4)" }}>{p.category_name}</span>}
            <h1 style={{ fontSize: "clamp(22px,3.4vw,32px)", fontWeight: 800, lineHeight: 1.5, margin: "12px 0 0" }}>{p.title}</h1>
          </div>
        </div>

        {/* meta bar */}
        <div className="panel" style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap", margin: "14px 0 26px", padding: "14px 20px" }}>
          <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
            <span style={{ width: 34, height: 34, borderRadius: 10, background: "linear-gradient(135deg,var(--purple),var(--purple-2))", color: "#fff", display: "grid", placeItems: "center", fontWeight: 800 }}>{(p.author_name || "ی").slice(0, 1)}</span>
            <b>{p.author_name || SITE.shortName}</b>
          </span>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>🗓 {faDate(p.published_at)}</span>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>⏱ {toFa(p.reading_time)} دقیقه مطالعه</span>
          <span style={{ fontSize: 12.5, color: "var(--muted)" }}>👁 {toFa(p.views)} بازدید</span>
          <button onClick={share} className="btn btn-ghost" style={{ height: 36, padding: "0 14px", fontSize: 12.5, marginRight: "auto" }}>↗ اشتراک‌گذاری</button>
        </div>

        {p.excerpt && (
          <div className="panel" style={{ borderRight: "4px solid var(--orange)", marginBottom: 18, fontSize: 15, lineHeight: 2, color: "var(--ink-soft)" }}>
            <b style={{ display: "block", marginBottom: 6, color: "var(--ink)", fontSize: 13.5 }}>خلاصه مقاله</b>
            {p.excerpt}
          </div>
        )}

        {(() => {
          // Table of contents from the article headings (HTML or ## format).
          const isHtml = /<[a-z][\s\S]*>/i.test(p.body || "");
          const heads = isHtml
            ? [...(p.body || "").matchAll(/<h2[^>]*>([\s\S]*?)<\/h2>/gi)].map((m) => m[1].replace(/<[^>]+>/g, "").trim())
            : [...(p.body || "").matchAll(/^##(?!#)\s*(.+)$/gm)].map((m) => m[1].trim());
          return heads.length >= 2 ? (
            <div className="panel" style={{ marginBottom: 18 }}>
              <b style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                <span style={{ width: 30, height: 30, borderRadius: 9, background: "var(--purple-soft)", color: "var(--purple)", display: "grid", placeItems: "center" }}>☰</span>
                فهرست مطالب
              </b>
              <ol style={{ margin: 0, paddingRight: 20, display: "flex", flexDirection: "column", gap: 7, fontSize: 13.5, color: "var(--ink-soft)" }}>
                {heads.map((h, i) => (<li key={i}>{h}</li>))}
              </ol>
            </div>
          ) : null;
        })()}

        {/* Article body inside a proper card. RTE posts store HTML; older
            seeded posts use the ## markdown-ish format. */}
        <div className="panel" style={{ padding: "clamp(18px,3.5vw,34px)" }}>
          {/<[a-z][\s\S]*>/i.test(p.body || "")
            ? <div className="post-html" dangerouslySetInnerHTML={{ __html: p.body }} />
            : <div className="post-html">{renderBody(p.body || "")}</div>}

          <div style={{ marginTop: 26, paddingTop: 16, borderTop: "1px dashed var(--line)", display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ fontSize: 12.5, color: "var(--muted)" }}>برچسب‌ها:</span>
            {p.category_name && <span className="badge purple">{p.category_name}</span>}
            {p.focus_keyword && <span className="badge amber">{p.focus_keyword}</span>}
            <span className="badge green">لوازم یدکی</span>
          </div>
        </div>

        {/* CTA */}
        <div className="wholesale" style={{ marginTop: 40, padding: 30 }}>
          <div className="in">
            <h2 style={{ fontSize: 20 }}>به دنبال قطعات با کیفیت هستید؟</h2>
            <p style={{ fontSize: 13.5 }}>بیش از ۱۲٬۰۰۰ کد کالای اصل با قیمت عمده در {SITE.shortName}.</p>
          </div>
          <Link href="/shop" className="btn btn-orange" style={{ height: 48, padding: "0 24px", position: "relative" }}>مشاهده فروشگاه</Link>
        </div>

        {/* related */}
        {related.length > 0 && (
          <section>
            <div className="sec-head"><h2 style={{ fontSize: 19 }}><span className="bar" />مقالات مرتبط</h2></div>
            {/* auto-fill (not auto-fit) keeps a single card at its natural width */}
            <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))" }}>
              {related.map((a) => (
                <Link key={a.id} href={`/blog/${encodeURIComponent(a.slug)}`} className="card" style={{ display: "block" }}>
                  <div className="thumb" style={{ height: 120, background: a.cover ? undefined : "radial-gradient(220px 130px at 80% 0%,rgba(255,138,61,.35),transparent),linear-gradient(135deg,var(--purple-deep),var(--purple-2))", color: "#fff" }}>
                    {a.cover
                      ? <img src={a.cover} alt={a.title} />
                      : <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.85)" strokeWidth="1.6"><path d="M4 4h16v16H4z" rx="2" /><path d="M8 9h8M8 13h8M8 17h5" /></svg>}
                  </div>
                  <div className="body">
                    <div style={{ fontWeight: 700, fontSize: 14, lineHeight: 1.7, minHeight: 0 }}>{a.title}</div>
                    <div style={{ fontSize: 11.5, color: "var(--muted)", marginTop: 8, display: "flex", gap: 10 }}>
                      <span>⏱ {toFa(a.reading_time)} دقیقه</span>
                      {a.category_name && <span className="badge purple" style={{ fontSize: 10.5, padding: "2px 8px" }}>{a.category_name}</span>}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}
      </article>
    </div>
  );
}
