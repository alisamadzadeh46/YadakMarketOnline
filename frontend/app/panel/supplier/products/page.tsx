"use client";
// Product manager: list/search, create/edit form, gallery upload and
// dynamic attribute rows — everything the supplier needs without Django admin.
import { useCallback, useEffect, useState } from "react";
import { api, errorMessage, errorStatus } from "@/lib/api";
import PriceField from "@/components/PriceField";
import { toast } from "@/lib/ui";
import { money, toFa } from "@/lib/format";
import SearchSelect from "@/components/SearchSelect";
import Pagination from "@/components/Pagination";
import { usePage } from "@/lib/usePage";

const EMPTY = {
  name: "", sku: "", brand: "", category: "", price: "", compare_at_price: "",
  stock: "", min_order_qty: 1, unit: "piece", short_description: "", description: "",
  is_active: true, is_featured: false, meta_title: "", meta_description: "", focus_keyword: "",
};

export default function SupplierProducts() {
  const [rows, setRows] = useState<any[]>([]);
  const [brands, setBrands] = useState<any[]>([]);
  const [cats, setCats] = useState<any[]>([]);
  // Empty for a plain supplier — the endpoint only answers the site owner, so
  // the selector below simply never renders for them.
  const [suppliers, setSuppliers] = useState<any[]>([]);
  // Every colour in the catalog; suppliers pick from these (and may add one).
  const [colors, setColors] = useState<any[]>([]);
  const [search, setSearch] = useState("");
  const [count, setCount] = useState(0);
  const [form, setForm] = useState<any>(null);   // editor state
  const [attrs, setAttrs] = useState<{ name_text: string; value: string }[]>([]);
  const [tiers, setTiers] = useState<{ min_qty: string; price: string }[]>([]);
  const [busy, setBusy] = useState(false);

  const [page, setPage] = usePage([search]);

  const load = useCallback(() =>
    api.get(`/catalog/manage/products/?page=${page}${search ? `&search=${encodeURIComponent(search)}` : ""}`)
      .then((d) => { setRows(d.results || d); setCount(d.count ?? (d.results || d).length); })
      .catch((e) => toast(errorMessage(e))), [page, search]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    api.get("/catalog/brands/").then(setBrands);
    api.get("/catalog/categories/").then(setCats);
    api.get("/catalog/manage/suppliers/").then(setSuppliers).catch(() => setSuppliers([]));
    api.get("/catalog/colors/").then(setColors).catch(() => setColors([]));
  }, []);

  const openEditor = (p?: any) => {
    if (!p) { setForm({ ...EMPTY }); setAttrs([{ name_text: "", value: "" }]); setTiers([]); return; }
    setForm({
      ...p,
      brand: p.brand?.id ?? p.brand,
      category: p.category?.id ?? p.category,
      // The API returns colours as objects but accepts ids on write.
      colors: (p.colors || []).map((c: any) => c.id ?? c),
    });
    setAttrs((p.attributes || []).map((a: any) => ({ name_text: a.name, value: a.value })));
    setTiers((p.tiers || []).map((t: any) => ({ min_qty: String(t.min_qty), price: String(t.price) })));
  };

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = { ...form, compare_at_price: form.compare_at_price || null };
      // colours ARE saved — they drive the swatches and the per-colour gallery.
      delete payload.images; delete payload.attributes;
      delete payload.sizes; delete payload.compatible_cars;
      let saved;
      if (form.id) saved = await api.patch(`/catalog/manage/products/${form.id}/`, payload);
      else saved = await api.post("/catalog/manage/products/", payload);
      // Persist dynamic attribute rows + volume price tiers in one go.
      const pid = saved.id || form.id;
      await api.post(`/catalog/manage/products/${pid}/attributes/`, {
        attributes: attrs.filter((a) => a.name_text && a.value),
      });
      await api.post(`/catalog/manage/products/${pid}/tiers/`, {
        tiers: tiers.filter((t) => t.min_qty && t.price),
      });
      toast("محصول ذخیره شد ✓");
      setForm(null);
      load();
    } catch (err) { toast(errorMessage(err)); }
    finally { setBusy(false); }
  };

  // Brand/category maintenance straight from the product form. Kind is the API
  // segment ("brands" | "categories"); both live under /catalog/manage/ and
  // both refresh the same lists so the new value is selectable immediately.
  const reloadTaxa = async () => {
    const [b, c] = await Promise.all([
      api.get("/catalog/brands/"),
      api.get("/catalog/categories/"),
    ]);
    setBrands(b.results || b);
    setCats(c.results || c);
  };

  const createTaxon = async (kind: "brands" | "categories", name: string) => {
    try {
      const made = await api.post(`/catalog/manage/${kind}/`, { name });
      await reloadTaxa();
      toast(kind === "brands" ? "برند ثبت شد ✓" : "دسته‌بندی ثبت شد ✓");
      return { id: made.id, name: made.name };
    } catch (e) {
      toast(errorMessage(e, "ثبت انجام نشد."));
      return null;
    }
  };

  const renameTaxon = async (kind: "brands" | "categories", id: number, name: string) => {
    try {
      await api.patch(`/catalog/manage/${kind}/${id}/`, { name });
      await reloadTaxa();
      toast("نام به‌روزرسانی شد ✓");
    } catch (e) {
      toast(errorMessage(e, "ویرایش انجام نشد."));
    }
  };

  const deleteTaxon = async (kind: "brands" | "categories", id: number) => {
    try {
      await api.del(`/catalog/manage/${kind}/${id}/`);
      await reloadTaxa();
      // Clear the field if the entry we just removed was the selected one.
      setForm((f: any) => ({
        ...f,
        brand: kind === "brands" && String(f.brand) === String(id) ? "" : f.brand,
        category: kind === "categories" && String(f.category) === String(id) ? "" : f.category,
      }));
      toast("حذف شد ✓");
    } catch (e) {
      toast(errorMessage(e, "حذف انجام نشد. ممکن است محصولی به آن وصل باشد."));
    }
  };

  const remove = async (id: number) => {
    if (!confirm("این محصول حذف شود؟")) return;
    try {
      await api.del(`/catalog/manage/products/${id}/`);
      toast("محصول حذف شد");
      load();
    } catch (err) {
      // 409 = the product appears on past invoices, so it cannot be erased.
      // Offer the thing the supplier actually wants: take it off the shop.
      if (errorStatus(err) === 409) {
        if (confirm(`${errorMessage(err)}\n\nهمین حالا غیرفعال شود؟`)) {
          try {
            await api.patch(`/catalog/manage/products/${id}/`, { is_active: false });
            toast("محصول غیرفعال شد و دیگر در فروشگاه نمایش داده نمی‌شود ✓");
            load();
          } catch (e) {
            toast(errorMessage(e, "غیرفعال‌سازی انجام نشد."));
          }
        }
        return;
      }
      // Anything else used to vanish silently — the button looked broken.
      toast(errorMessage(err, "حذف محصول انجام نشد."));
    }
  };

  const uploadImage = async (file: File, colorId?: number | null) => {
    const fd = new FormData();
    fd.append("image", file);
    if (colorId) fd.append("color", String(colorId));
    const img = await api.post(`/catalog/manage/products/${form.id}/images/`, fd);
    setForm({ ...form, images: [...(form.images || []), img] });
    toast(colorId ? "تصویر رنگ افزوده شد ✓" : "تصویر افزوده شد ✓");
  };

  /** Re-tag an already uploaded photo, so a mistake doesn't mean re-uploading. */
  const setImageColor = async (imageId: number, colorId: number | null) => {
    try {
      await api.patch(`/catalog/manage/products/${form.id}/images/${imageId}/`, { color: colorId });
      setForm({
        ...form,
        images: form.images.map((i: any) => (i.id === imageId ? { ...i, color: colorId } : i)),
      });
    } catch (err) { toast(errorMessage(err)); }
  };

  /** Add a colour that isn't in the list yet and attach it to this product. */
  const addColor = async (name: string) => {
    const clean = name.trim();
    if (!clean) return;
    try {
      const c = await api.post("/catalog/manage/colors/", { name: clean });
      setColors((prev) => (prev.some((x) => x.id === c.id) ? prev : [...prev, c]));
      setForm((f: any) => ({ ...f, colors: [...(f.colors || []), c.id] }));
      toast(`رنگ «${c.name}» افزوده شد ✓`);
    } catch (err) { toast(errorMessage(err)); }
  };
  const deleteImage = async (imageId: number) => {
    await api.del(`/catalog/manage/products/${form.id}/images/${imageId}/`);
    setForm({ ...form, images: form.images.filter((i: any) => i.id !== imageId) });
  };

  if (form) {
    return (
      <form className="view" onSubmit={save}>
        <div className="between" style={{ marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>{form.id ? `ویرایش: ${form.name}` : "محصول جدید"}</h2>
          <button type="button" className="btn btn-ghost" style={{ height: 40, padding: "0 16px" }} onClick={() => setForm(null)}>بازگشت به لیست</button>
        </div>

        <div className="panel" style={{ marginBottom: 14 }}>
          <b style={{ display: "block", marginBottom: 12 }}>مشخصات اصلی</b>
          <div className="fgrid">
            <div className="field"><label>نام محصول *</label><input className="inp" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="field"><label>شماره فنی (SKU) *</label><input className="inp" required dir="ltr" value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} /></div>
            <div className="field"><label>برند *</label>
              <SearchSelect
                value={String(form.brand || "")}
                items={brands.map((b) => ({ id: b.id, name: b.name }))}
                onChange={(v) => setForm({ ...form, brand: v })}
                placeholder="انتخاب برند…"
                searchPlaceholder="جست‌وجوی برند…"
                createLabel="ثبت سریع برند"
                onCreate={(name) => createTaxon("brands", name)}
                onRename={(id, name) => renameTaxon("brands", id, name)}
                onDelete={(id) => deleteTaxon("brands", id)}
              /></div>
            <div className="field"><label>دسته‌بندی *</label>
              <SearchSelect
                value={String(form.category || "")}
                items={cats.map((c) => ({ id: c.id, name: c.name }))}
                onChange={(v) => setForm({ ...form, category: v })}
                placeholder="انتخاب دسته‌بندی…"
                searchPlaceholder="جست‌وجوی دسته‌بندی…"
                createLabel="ثبت سریع دسته‌بندی"
                onCreate={(name) => createTaxon("categories", name)}
                onRename={(id, name) => renameTaxon("categories", id, name)}
                onDelete={(id) => deleteTaxon("categories", id)}
              /></div>
            {/* Owner-only: file the product under another supplier so it shows
                up in their panel. The API ignores this field for non-owners. */}
            {suppliers.length > 0 && (
              <div className="field">
                <label>تأمین‌کننده</label>
                <SearchSelect
                  value={String(form.supplier || "")}
                  items={suppliers.map((u: any) => ({ id: u.id, name: u.name }))}
                  onChange={(v) => setForm({ ...form, supplier: v ? Number(v) : null })}
                  placeholder="خودم (پیش‌فرض)"
                  searchPlaceholder="جست‌وجوی تأمین‌کننده…"
                />
              </div>
            )}
            <div className="field"><label>قیمت عمده (تومان) *</label><PriceField required value={form.price} onChange={(v) => setForm({ ...form, price: v })} /></div>
            <div className="field"><label>قیمت قبل تخفیف</label><PriceField value={form.compare_at_price || ""} onChange={(v) => setForm({ ...form, compare_at_price: v })} /></div>
            <div className="field"><label>موجودی *</label><PriceField required value={form.stock} onChange={(v) => setForm({ ...form, stock: v })} /></div>
            <div className="field"><label>حداقل سفارش عمده</label><PriceField value={form.min_order_qty} onChange={(v) => setForm({ ...form, min_order_qty: v })} /></div>
            <div className="field"><label>وضعیت اصالت</label><input className="inp" placeholder="مثلا: اصل شرکتی" value={form.authenticity ?? "اصل شرکتی"} onChange={(e) => setForm({ ...form, authenticity: e.target.value })} /></div>
            <div className="field"><label>گارانتی</label><input className="inp" placeholder="مثلا: ۱۸ ماه گارانتی شرکتی" value={form.warranty_text || ""} onChange={(e) => setForm({ ...form, warranty_text: e.target.value })} /></div>
            <div className="field full"><label>توضیح کوتاه</label><input className="inp" value={form.short_description || ""} onChange={(e) => setForm({ ...form, short_description: e.target.value })} /></div>
            <div className="field full"><label>توضیحات کامل</label><textarea className="inp" rows={4} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <div className="row">
            <label style={{ display: "flex", gap: 7, alignItems: "center", fontSize: 13.5, cursor: "pointer" }}>
              <input type="checkbox" checked={!!form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} style={{ accentColor: "var(--purple)" }} /> منتشر شده
            </label>
            <label style={{ display: "flex", gap: 7, alignItems: "center", fontSize: 13.5, cursor: "pointer" }}>
              <input type="checkbox" checked={!!form.is_featured} onChange={(e) => setForm({ ...form, is_featured: e.target.checked })} style={{ accentColor: "var(--orange)" }} /> محصول ویژه
            </label>
          </div>
        </div>

        {/* Colours: the swatches a buyer sees, and what each photo can be
            tagged with below. Any supplier may add a shade that is missing. */}
        <div className="panel" style={{ marginBottom: 14 }}>
          <b style={{ display: "block", marginBottom: 4 }}>رنگ‌های این محصول</b>
          <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 12, lineHeight: 1.9 }}>
            رنگ‌های انتخاب‌شده به‌صورت سواچ در صفحه‌ی محصول نمایش داده می‌شوند و خریدار
            می‌تواند رنگ دلخواهش را انتخاب کند؛ رنگ انتخابی در سبد خرید و سفارش هم ثبت می‌شود.
          </div>
          <div className="row" style={{ flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
            {colors.map((c: any) => {
              const on = (form.colors || []).includes(c.id);
              return (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => setForm({
                    ...form,
                    colors: on
                      ? (form.colors || []).filter((x: number) => x !== c.id)
                      : [...(form.colors || []), c.id],
                  })}
                  className={`colorpick ${on ? "on" : ""}`}
                >
                  <i style={{ background: c.hex_code || "#ccc" }} />
                  {c.name}
                </button>
              );
            })}
            {!colors.length && <span style={{ fontSize: 12.5, color: "var(--muted)" }}>هنوز رنگی تعریف نشده.</span>}
          </div>
          <div className="row" style={{ gap: 8 }}>
            <input
              className="inp"
              style={{ maxWidth: 220 }}
              placeholder="افزودن رنگ جدید (مثلا بژ طلایی)"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  addColor((e.target as HTMLInputElement).value);
                  (e.target as HTMLInputElement).value = "";
                }
              }}
            />
            <span style={{ fontSize: 12, color: "var(--muted)", alignSelf: "center" }}>
              نام رنگ را بنویسید و Enter بزنید
            </span>
          </div>
        </div>

        {form.id ? (
          <div className="panel" style={{ marginBottom: 14 }}>
            <b style={{ display: "block", marginBottom: 4 }}>گالری تصاویر</b>
            <div style={{ fontSize: 12.5, color: "var(--muted)", marginBottom: 12, lineHeight: 1.9 }}>
              زیر هر تصویر می‌توانید رنگ آن را مشخص کنید. با انتخاب رنگ، آن تصویر فقط وقتی
              نمایش داده می‌شود که خریدار همان رنگ را انتخاب کند؛ «همه‌ی رنگ‌ها» یعنی تصویر
              برای هر رنگی نشان داده شود.
            </div>
            <div className="row" style={{ marginBottom: 12, flexWrap: "wrap", alignItems: "flex-start" }}>
              {(form.images || []).map((img: any) => (
                <div key={img.id} style={{ position: "relative", width: 130 }}>
                  <img src={img.image} alt="" style={{ width: 130, height: 100, objectFit: "contain", background: "#fff", padding: 4, borderRadius: 12, border: "1px solid var(--line)" }} />
                  <button type="button" onClick={() => deleteImage(img.id)} style={{ position: "absolute", top: 4, left: 4, background: "var(--red)", color: "#fff", borderRadius: 8, width: 24, height: 24 }}>×</button>
                  <select
                    className="inp"
                    style={{ marginTop: 6, height: 34, fontSize: 12, padding: "0 8px" }}
                    value={img.color ?? ""}
                    onChange={(e) => setImageColor(img.id, e.target.value ? Number(e.target.value) : null)}
                  >
                    <option value="">همه‌ی رنگ‌ها</option>
                    {colors
                      .filter((c: any) => (form.colors || []).includes(c.id))
                      .map((c: any) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
              ))}
            </div>
            <input className="inp" type="file" accept="image/*" onChange={(e) => e.target.files?.[0] && uploadImage(e.target.files[0])} />
            {!(form.colors || []).length && (
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 8 }}>
                برای تگ‌کردن تصویر با رنگ، ابتدا رنگ‌های محصول را در بخش بالا انتخاب کنید.
              </div>
            )}
          </div>
        ) : (
          <div className="panel" style={{ marginBottom: 14, color: "var(--muted)", fontSize: 13.5 }}>
            پس از ذخیره‌ی محصول، امکان بارگذاری تصاویر فعال می‌شود.
          </div>
        )}

        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="between" style={{ marginBottom: 12 }}>
            <b>ویژگی‌های پویا (مشخصات فنی)</b>
            <button type="button" className="act-edit list-actions" onClick={() => setAttrs([...attrs, { name_text: "", value: "" }])}>+ ردیف جدید</button>
          </div>
          {attrs.map((a, i) => (
            <div key={i} className="row" style={{ marginBottom: 8 }}>
              <input className="inp" style={{ flex: 1, minWidth: 140 }} placeholder="نام ویژگی (مثلا جنس)" value={a.name_text} onChange={(e) => setAttrs(attrs.map((x, k) => k === i ? { ...x, name_text: e.target.value } : x))} />
              <input className="inp" style={{ flex: 2, minWidth: 160 }} placeholder="مقدار (مثلا سرامیک)" value={a.value} onChange={(e) => setAttrs(attrs.map((x, k) => k === i ? { ...x, value: e.target.value } : x))} />
              <button type="button" className="act-del list-actions" onClick={() => setAttrs(attrs.filter((_, k) => k !== i))}>حذف</button>
            </div>
          ))}
        </div>

        <div className="panel" style={{ marginBottom: 14 }}>
          <div className="between" style={{ marginBottom: 6 }}>
            <b>قیمت پلکانی عمده</b>
            <button type="button" className="act-edit list-actions" onClick={() => setTiers([...tiers, { min_qty: "", price: "" }])}>+ پله جدید</button>
          </div>
          <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
            مثلا: از ۵۰ عدد به بالا، قیمت واحد ارزان‌تر. قیمت پله باید از قیمت پایه کمتر باشد.
          </div>
          {tiers.map((t, i) => (
            <div key={i} className="row" style={{ marginBottom: 8 }}>
              <PriceField style={{ flex: 1, minWidth: 120 }} placeholder="از تعداد (مثلا ۵۰)" value={t.min_qty} onChange={(v) => setTiers(tiers.map((x, k) => k === i ? { ...x, min_qty: v } : x))} />
              <PriceField style={{ flex: 2, minWidth: 160 }} placeholder="قیمت واحد (تومان)" value={t.price} onChange={(v) => setTiers(tiers.map((x, k) => k === i ? { ...x, price: v } : x))} />
              <button type="button" className="act-del list-actions" onClick={() => setTiers(tiers.filter((_, k) => k !== i))}>حذف</button>
            </div>
          ))}
          {!tiers.length && <div style={{ fontSize: 12.5, color: "var(--muted)" }}>پله‌ای تعریف نشده — قیمت پایه برای همه تعدادها اعمال می‌شود.</div>}
        </div>

        <div className="panel" style={{ marginBottom: 14 }}>
          <b style={{ display: "block", marginBottom: 12 }}>سئو</b>
          <div className="fgrid">
            <div className="field"><label>کلمه کلیدی هدف</label><input className="inp" value={form.focus_keyword || ""} onChange={(e) => setForm({ ...form, focus_keyword: e.target.value })} /></div>
            <div className="field"><label>عنوان سئو</label><input className="inp" value={form.meta_title || ""} onChange={(e) => setForm({ ...form, meta_title: e.target.value })} /></div>
            <div className="field full"><label>توضیح متا</label><textarea className="inp" rows={2} value={form.meta_description || ""} onChange={(e) => setForm({ ...form, meta_description: e.target.value })} /></div>
          </div>
        </div>

        <button className="btn btn-purple" style={{ height: 50, padding: "0 34px", fontSize: 15 }} disabled={busy}>{busy ? "در حال ذخیره…" : "ذخیره محصول"}</button>
      </form>
    );
  }

  return (
    <div>
      <div className="between" style={{ marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800 }}>محصولات</h2>
        <button className="btn btn-purple" style={{ height: 42, padding: "0 18px" }} onClick={() => openEditor()}>+ محصول جدید</button>
      </div>
      <div className="shopbar">
        <input className="inp" style={{ maxWidth: 320 }} placeholder="جستجوی نام محصول…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <div style={{ fontSize: 13, color: "var(--muted)" }}><b className="mono">{toFa(count)}</b> محصول</div>
      </div>
      <div className="panel tablewrap">
        {/* min-width forces horizontal scroll on a phone instead of squeezing
            the name column down to one character per line. */}
        <table className="tbl" style={{ minWidth: 680 }}>
          <thead><tr><th>نام</th><th>SKU</th><th>قیمت</th><th>موجودی</th><th>وضعیت</th><th>عملیات</th></tr></thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.id}>
                <td className="wrap" style={{ maxWidth: 300 }}><b>{p.name}</b></td>
                <td className="mono">{toFa(p.sku)}</td>
                <td className="mono">{money(p.price)}</td>
                <td className="mono">{toFa(p.stock)}</td>
                <td>{p.is_active ? <span className="badge green">منتشر</span> : <span className="badge amber">پیش‌نویس</span>}</td>
                <td>
                  <div className="list-actions">
                    <button className="act-edit" onClick={() => openEditor(p)}>ویرایش</button>
                    <button className="act-del" onClick={() => remove(p.id)}>حذف</button>
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && <tr><td colSpan={6} style={{ textAlign: "center", color: "var(--muted)" }}>محصولی نیست.</td></tr>}
          </tbody>
        </table>
      </div>
      <Pagination page={page} count={count} onChange={setPage} />
    </div>
  );
}
