"use client";
// Blog listing: dynamic category chips (admin-managed), search and sorting.
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toFa } from "@/lib/format";
import NiceSelect from "@/components/NiceSelect";
import { ISearch } from "@/components/Icon";
import { SITE } from "@/lib/site";

const SORTS = [
  { value: "-published_at", label: "جدیدترین" },
  { value: "published_at", label: "قدیمی‌ترین" },
  { value: "-views", label: "پربازدیدترین" },
];

export default function Blog() {
  const [posts, setPosts] = useState<any[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  const [cat, setCat] = useState("");
  const [sort, setSort] = useState("-published_at");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/blog/categories/").then((d) => setCats(d.results || d)).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    const p = new URLSearchParams({ ordering: sort });
    if (cat) p.set("category", cat);
    if (q) p.set("search", q);
    api.get(`/blog/posts/?${p}`)
      .then((d) => setPosts(d.results || d))
      .finally(() => setLoading(false));
  }, [cat, sort, q]);

  return (
    <div className="view">
      <div className="sec-head"><h2><span className="bar" />وبلاگ فنی {SITE.shortName}</h2></div>

      {/* toolbar: category chips + search + sort */}
      <div className="shopbar" style={{ gap: 14 }}>
        <div className="fchips">
          <button className={!cat ? "on" : ""} onClick={() => setCat("")}>همه</button>
          {cats.map((c) => (
            <button key={c.id} className={cat === String(c.id) ? "on" : ""} onClick={() => setCat(String(c.id))}>{c.name}</button>
          ))}
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <div className="search" style={{ display: "flex", height: 42, maxWidth: 240 }}>
            <ISearch size={16} />
            <input placeholder="جستجو در مقالات…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <NiceSelect value={sort} onChange={setSort} options={SORTS} style={{ minWidth: 150 }} />
        </div>
      </div>

      {loading ? (
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))" }}>
          {[1, 2, 3].map((i) => (<div key={i} className="skel" style={{ height: 280 }} />))}
        </div>
      ) : (
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))" }}>
          {posts.map((a) => (
            <Link key={a.id} href={`/blog/${encodeURIComponent(a.slug)}`} className="card" style={{ display: "block" }}>
              <div className="thumb" style={{ height: 170, background: a.cover ? undefined : "radial-gradient(280px 160px at 80% 0%,rgba(255,138,61,.35),transparent),linear-gradient(135deg,var(--purple-deep),var(--purple-2))", color: "#fff", fontWeight: 700 }}>
                {a.cover ? <img src={a.cover} alt={a.title} /> : "مقاله فنی"}
              </div>
              <div className="body">
                <div style={{ display: "flex", gap: 8, alignItems: "center", fontSize: 11.5, color: "var(--muted)" }}>
                  {a.category_name && <span className="badge purple" style={{ fontSize: 11 }}>{a.category_name}</span>}
                  <span>⏱ {toFa(a.reading_time)} دقیقه</span>
                  <span>👁 {toFa(a.views)}</span>
                </div>
                <div style={{ fontWeight: 700, fontSize: 15.5, margin: "10px 0 8px", lineHeight: 1.7 }}>{a.title}</div>
                <div style={{ fontSize: 13, color: "var(--muted)", lineHeight: 1.9 }}>{a.excerpt}</div>
                <div style={{ marginTop: 12, fontSize: 12, color: "var(--purple)", fontWeight: 700 }}>ادامه مطلب ›</div>
              </div>
            </Link>
          ))}
          {!posts.length && (
            <div className="center-empty" style={{ gridColumn: "1 / -1" }}>
              <div style={{ fontSize: 42 }}>📄</div>
              <p>مقاله‌ای با این فیلترها یافت نشد.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
