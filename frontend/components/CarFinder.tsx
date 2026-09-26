"use client";
// "Find the right part for your car" — the missing path the homepage lacked:
// pick a maker, then a model (from real CarModel data, no invented options),
// optionally a category, and jump straight to the filtered shop results.
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import NiceSelect from "./NiceSelect";

type CarModel = { id: number; name: string; brand: number; brand_name: string };
type Category = { id: number; name: string };

export default function CarFinder() {
  const router = useRouter();
  const [cars, setCars] = useState<CarModel[]>([]);
  const [cats, setCats] = useState<Category[]>([]);
  const [maker, setMaker] = useState("");
  const [model, setModel] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    api.get<CarModel[]>("/catalog/cars/", { auth: false }).then((d: any) => setCars(d.results || d)).catch(() => {});
    api.get<Category[]>("/catalog/categories/", { auth: false }).then(setCats).catch(() => {});
  }, []);

  const makers = useMemo(() => {
    const seen = new Map<string, number>();
    cars.forEach((c) => { if (!seen.has(c.brand_name)) seen.set(c.brand_name, c.brand); });
    return Array.from(seen.entries()).sort((a, b) => a[0].localeCompare(b[0], "fa"));
  }, [cars]);

  const models = useMemo(
    () => cars.filter((c) => String(c.brand) === maker).sort((a, b) => a.name.localeCompare(b.name, "fa")),
    [cars, maker]
  );

  const go = () => {
    const p = new URLSearchParams();
    if (model) p.set("car", model);
    if (category) p.set("category", category);
    router.push(`/shop?${p.toString()}`);
  };

  return (
    <section className="carfinder">
      <div className="cf-head">
        <div className="cf-ic">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M5 13l1.6-4.5A2 2 0 0 1 8.5 7h7a2 2 0 0 1 1.9 1.5L19 13v5h-2.5v-1.5h-9V18H5z" /><circle cx="7.8" cy="15" r="1" /><circle cx="16.2" cy="15" r="1" /></svg>
        </div>
        <div>
          <b>قطعه مناسب خودروی خود را پیدا کنید</b>
          <span>برند و مدل خودرو را انتخاب کنید تا فقط قطعات سازگار را ببینید.</span>
        </div>
      </div>
      <div className="cf-row">
        <NiceSelect value={maker} onChange={(v) => { setMaker(v); setModel(""); }} style={{ flex: 1, minWidth: 150 }}
          options={[{ value: "", label: "برند خودرو" }, ...makers.map(([name, id]) => ({ value: String(id), label: name }))]} />
        <NiceSelect value={model} onChange={setModel} style={{ flex: 1, minWidth: 150 }}
          options={[{ value: "", label: maker ? "مدل خودرو" : "ابتدا برند را انتخاب کنید" }, ...models.map((m) => ({ value: String(m.id), label: m.name }))]} />
        <NiceSelect value={category} onChange={setCategory} style={{ flex: 1, minWidth: 150 }}
          options={[{ value: "", label: "دسته قطعه (اختیاری)" }, ...cats.map((c) => ({ value: String(c.id), label: c.name }))]} />
        <button className="btn btn-orange cf-go" disabled={!model} onClick={go}>نمایش قطعات سازگار ›</button>
      </div>
    </section>
  );
}
