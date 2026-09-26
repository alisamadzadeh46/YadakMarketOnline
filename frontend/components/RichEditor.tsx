"use client";
// Word-style rich text editor — zero external deps (no CDN).
// Groups: history · text style · headings · alignment · lists/quote ·
// color/highlight · link · media upload · clear · fullscreen. Emits HTML.
import { useEffect, useRef, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { toast } from "@/lib/ui";
import { toFa } from "@/lib/format";

const COLORS = ["#211A33", "#5B2E9E", "#F26A1B", "#1F9D63", "#E24545", "#2F53E6"];
const HILITES = ["#FFF3C4", "#EADDFB", "#FDE2CF", "#D7F2E3"];

function TB({ label, title, onRun, active }: { label: React.ReactNode; title: string; onRun: () => void; active?: boolean }) {
  return (
    <button
      type="button"
      title={title}
      onMouseDown={(e) => e.preventDefault()}
      onClick={onRun}
      style={{
        padding: "7px 9px", borderRadius: 8, fontSize: 13, fontWeight: 700, minWidth: 32,
        color: active ? "#fff" : "var(--ink-soft)", background: active ? "var(--purple)" : "transparent",
      }}
      onMouseEnter={(e) => { if (!active) e.currentTarget.style.background = "var(--purple-soft)"; }}
      onMouseLeave={(e) => { if (!active) e.currentTarget.style.background = "transparent"; }}
    >
      {label}
    </button>
  );
}

const Sep = () => <span style={{ width: 1, alignSelf: "stretch", background: "var(--line)", margin: "4px 3px" }} />;

export default function RichEditor({ value, onChange }: { value: string; onChange: (html: string) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [full, setFull] = useState(false);
  const [words, setWords] = useState(0);
  const [palette, setPalette] = useState<"none" | "color" | "hilite">("none");

  const count = () => {
    const text = ref.current?.innerText || "";
    setWords(text.trim() ? text.trim().split(/\s+/).length : 0);
  };

  // Seed the editable area once; afterwards the DOM is the source of truth.
  useEffect(() => {
    if (ref.current && ref.current.innerHTML === "" && value) {
      ref.current.innerHTML = value;
      count();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const emit = () => { onChange(ref.current?.innerHTML || ""); count(); };
  const cmd = (command: string, arg?: string) => {
    ref.current?.focus();
    document.execCommand(command, false, arg);
    emit();
  };

  const addLink = () => {
    const url = prompt("آدرس لینک:", "https://");
    if (url) cmd("createLink", url);
  };

  const upload = async (file: File) => {
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/blog/manage/upload/", fd);
      ref.current?.focus();
      document.execCommand(
        "insertHTML", false,
        r.is_video
          ? `<video controls style="max-width:100%;border-radius:12px" src="${r.url}"></video><p></p>`
          : `<img src="${r.url}" alt="" style="max-width:100%;border-radius:12px" /><p></p>`
      );
      emit();
      toast("فایل در متن درج شد ✓");
    } catch (e) { toast(errorMessage(e)); }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  return (
    <div style={{
      border: "1.5px solid var(--line)", borderRadius: 14, overflow: "hidden", background: "var(--card)",
      ...(full ? { position: "fixed", inset: 12, zIndex: 300, display: "flex", flexDirection: "column" } : {}),
    }}>
      {/* toolbar */}
      <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1, padding: 8, borderBottom: "1px solid var(--line)", background: "var(--paper)", position: "sticky", top: 0, zIndex: 5 }}>
        <TB label="↩" title="واگرد" onRun={() => cmd("undo")} />
        <TB label="↪" title="ازنو" onRun={() => cmd("redo")} />
        <Sep />
        <TB label={<b>B</b>} title="پررنگ" onRun={() => cmd("bold")} />
        <TB label={<i>I</i>} title="مورب" onRun={() => cmd("italic")} />
        <TB label={<u>U</u>} title="زیرخط" onRun={() => cmd("underline")} />
        <TB label={<s>S</s>} title="خط‌خورده" onRun={() => cmd("strikeThrough")} />
        <Sep />
        <TB label="H2" title="تیتر" onRun={() => cmd("formatBlock", "<h2>")} />
        <TB label="H3" title="زیرتیتر" onRun={() => cmd("formatBlock", "<h3>")} />
        <TB label="¶" title="پاراگراف" onRun={() => cmd("formatBlock", "<p>")} />
        <Sep />
        <TB label="⇤" title="راست‌چین" onRun={() => cmd("justifyRight")} />
        <TB label="↔" title="وسط‌چین" onRun={() => cmd("justifyCenter")} />
        <TB label="⇥" title="چپ‌چین" onRun={() => cmd("justifyLeft")} />
        <Sep />
        <TB label="•" title="لیست" onRun={() => cmd("insertUnorderedList")} />
        <TB label="۱." title="لیست عددی" onRun={() => cmd("insertOrderedList")} />
        <TB label="❝" title="نقل‌قول" onRun={() => cmd("formatBlock", "<blockquote>")} />
        <TB label="―" title="خط جداکننده" onRun={() => cmd("insertHorizontalRule")} />
        <Sep />
        <TB label={<span style={{ borderBottom: "3px solid #F26A1B" }}>A</span>} title="رنگ متن" onRun={() => setPalette(palette === "color" ? "none" : "color")} active={palette === "color"} />
        <TB label="🖍" title="هایلایت" onRun={() => setPalette(palette === "hilite" ? "none" : "hilite")} active={palette === "hilite"} />
        <Sep />
        <TB label="🔗" title="لینک" onRun={addLink} />
        <TB label="⛓̸" title="حذف لینک" onRun={() => cmd("unlink")} />
        <TB label={uploading ? "…" : "🖼"} title="درج تصویر/ویدئو" onRun={() => fileRef.current?.click()} />
        <TB label="⌫" title="پاک‌کردن قالب‌بندی" onRun={() => cmd("removeFormat")} />
        <span style={{ marginRight: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <span className="mono" style={{ fontSize: 11.5, color: "var(--muted)" }}>{toFa(words)} کلمه</span>
          <TB label={full ? "🗗" : "⛶"} title={full ? "خروج از تمام‌صفحه" : "تمام‌صفحه"} onRun={() => setFull(!full)} active={full} />
        </span>
        <input ref={fileRef} type="file" accept="image/*,video/mp4,video/webm" hidden
          onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
      </div>

      {/* color palettes */}
      {palette !== "none" && (
        <div style={{ display: "flex", gap: 6, padding: "8px 12px", borderBottom: "1px solid var(--line)", background: "var(--paper)" }}>
          {(palette === "color" ? COLORS : HILITES).map((c) => (
            <button key={c} type="button" onMouseDown={(e) => e.preventDefault()}
              onClick={() => { cmd(palette === "color" ? "foreColor" : "hiliteColor", c); setPalette("none"); }}
              style={{ width: 26, height: 26, borderRadius: 8, background: c, border: "2px solid var(--card)", boxShadow: "0 0 0 1px var(--line)" }} />
          ))}
        </div>
      )}

      <div
        ref={ref}
        contentEditable
        suppressContentEditableWarning
        onInput={emit}
        className="post-html"
        style={{ minHeight: full ? "auto" : 340, flex: full ? 1 : undefined, overflow: "auto", padding: "16px 18px", outline: "none", background: "var(--card)" }}
        data-placeholder="متن مقاله را اینجا بنویسید…"
      />
    </div>
  );
}
