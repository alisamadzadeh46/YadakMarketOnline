"""A Yoast-style content analyzer (Persian-aware).

Given a piece of content (title, meta, focus keyword, slug, body) it returns:
  * an overall 0-100 score,
  * a checklist of pass/warn/fail signals with human messages, and
  * concrete auto-fix suggestions (meta description, slug, meta title).

It is intentionally dependency-free and heuristic — good enough to guide an
author the way the WordPress Yoast plugin does, without external services.
"""

import re

GOOD, OK, BAD = "good", "ok", "bad"
_SCORE = {GOOD: 1.0, OK: 0.5, BAD: 0.0}


def _normalize(text: str) -> str:
    """Normalize Arabic vs Persian letters and collapse whitespace/casing."""
    if not text:
        return ""
    text = text.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def analyze(*, title="", meta_title="", meta_description="", focus_keyword="", slug="", body=""):
    kw = _normalize(focus_keyword)
    plain = _strip_html(body)
    plain_n = _normalize(plain)
    words = plain.split()
    word_count = len(words)
    # Persian + latin sentence terminators.
    sentences = [s for s in re.split(r"[.!?؟\n]+", plain) if s.strip()]
    first_paragraph = _normalize((body or "").split("\n\n")[0])

    checks = []

    def add(cid, label, status, message):
        checks.append({"id": cid, "label": label, "status": status, "message": message})

    # --- Focus keyword presence ------------------------------------------
    if not kw:
        add("keyword", "کلمه کلیدی هدف", BAD, "کلمه کلیدی هدف تعیین نشده است.")
    else:
        add("keyword", "کلمه کلیدی هدف", GOOD, f"کلمه کلیدی: «{focus_keyword}»")

        title_hit = kw in _normalize(meta_title or title)
        add(
            "kw_title",
            "کلمه کلیدی در عنوان",
            GOOD if title_hit else BAD,
            "کلمه کلیدی در عنوان آمده است." if title_hit else "کلمه کلیدی را در عنوان بیاورید.",
        )

        md_hit = kw in _normalize(meta_description)
        add(
            "kw_meta",
            "کلمه کلیدی در توضیح متا",
            GOOD if md_hit else BAD,
            "کلمه کلیدی در توضیح متا آمده است." if md_hit else "کلمه کلیدی را در توضیح متا بیاورید.",
        )

        slug_hit = kw.replace(" ", "-") in _normalize(slug).replace(" ", "-")
        add(
            "kw_slug",
            "کلمه کلیدی در نشانی (اسلاگ)",
            GOOD if slug_hit else OK,
            "کلمه کلیدی در اسلاگ آمده است." if slug_hit else "بهتر است کلمه کلیدی در اسلاگ باشد.",
        )

        intro_hit = kw in first_paragraph
        add(
            "kw_intro",
            "کلمه کلیدی در پاراگراف اول",
            GOOD if intro_hit else OK,
            "کلمه کلیدی در ابتدای متن آمده است." if intro_hit else "کلمه کلیدی را در پاراگراف نخست بیاورید.",
        )

        # Keyword density (occurrences / word_count).
        occurrences = plain_n.count(kw) if kw else 0
        density = (occurrences / word_count * 100) if word_count else 0
        if 0.5 <= density <= 2.5:
            add("density", "تراکم کلمه کلیدی", GOOD, f"تراکم مناسب است ({density:.1f}٪).")
        elif density < 0.5:
            add("density", "تراکم کلمه کلیدی", OK, f"تراکم کم است ({density:.1f}٪).")
        else:
            add("density", "تراکم کلمه کلیدی", BAD, f"تراکم زیاد است ({density:.1f}٪) — خطر اسپم.")

    # --- Meta title length -----------------------------------------------
    tlen = len(meta_title or title)
    if 30 <= tlen <= 60:
        add("title_len", "طول عنوان سئو", GOOD, f"طول عنوان مناسب است ({tlen} کاراکتر).")
    elif tlen == 0:
        add("title_len", "طول عنوان سئو", BAD, "عنوان سئو خالی است.")
    else:
        add("title_len", "طول عنوان سئو", OK, f"طول عنوان ({tlen}) خارج از بازه ۳۰ تا ۶۰ است.")

    # --- Meta description length -----------------------------------------
    dlen = len(meta_description)
    if 120 <= dlen <= 160:
        add("meta_len", "طول توضیح متا", GOOD, f"طول توضیح متا مناسب است ({dlen} کاراکتر).")
    elif dlen == 0:
        add("meta_len", "طول توضیح متا", BAD, "توضیح متا خالی است.")
    else:
        add("meta_len", "طول توضیح متا", OK, f"طول توضیح متا ({dlen}) بین ۱۲۰ تا ۱۶۰ نیست.")

    # --- Content length ---------------------------------------------------
    if word_count >= 300:
        add("length", "طول محتوا", GOOD, f"محتوا کافی است ({word_count} کلمه).")
    elif word_count >= 150:
        add("length", "طول محتوا", OK, f"محتوا کوتاه است ({word_count} کلمه).")
    else:
        add("length", "طول محتوا", BAD, f"محتوا خیلی کوتاه است ({word_count} کلمه).")

    # --- Subheadings ------------------------------------------------------
    has_headings = bool(re.search(r"<h[2-4][ >]|^#{2,}\s", body or "", re.MULTILINE))
    add(
        "headings",
        "زیرعنوان‌ها",
        GOOD if has_headings else OK,
        "زیرعنوان دارد." if has_headings else "برای خوانایی بهتر از زیرعنوان استفاده کنید.",
    )

    # --- Links ------------------------------------------------------------
    has_links = bool(re.search(r"<a\s|https?://", body or ""))
    add(
        "links",
        "پیوندها",
        GOOD if has_links else OK,
        "محتوا دارای پیوند است." if has_links else "افزودن پیوند داخلی/خارجی توصیه می‌شود.",
    )

    # --- Images alt text --------------------------------------------------
    imgs = re.findall(r"<img[^>]*>", body or "")
    if imgs:
        missing_alt = [i for i in imgs if "alt=" not in i or 'alt=""' in i]
        add(
            "img_alt",
            "متن جایگزین تصاویر",
            GOOD if not missing_alt else BAD,
            "همه تصاویر alt دارند." if not missing_alt else f"{len(missing_alt)} تصویر بدون alt است.",
        )

    # --- Readability: average sentence length -----------------------------
    if sentences:
        avg_len = word_count / len(sentences)
        if avg_len <= 20:
            add("readability", "خوانایی", GOOD, f"جملات کوتاه و خوانا هستند (میانگین {avg_len:.0f} کلمه).")
        elif avg_len <= 30:
            add("readability", "خوانایی", OK, f"جملات کمی بلند هستند (میانگین {avg_len:.0f} کلمه).")
        else:
            add("readability", "خوانایی", BAD, f"جملات خیلی بلند هستند (میانگین {avg_len:.0f} کلمه).")

    # --- Overall score ----------------------------------------------------
    score = round(sum(_SCORE[c["status"]] for c in checks) / len(checks) * 100) if checks else 0

    return {
        "score": score,
        "rating": "good" if score >= 80 else "ok" if score >= 50 else "bad",
        "word_count": word_count,
        "checks": checks,
        "suggestions": suggest(title=title, meta_description=meta_description, slug=slug, body=plain),
    }


def suggest(*, title="", meta_description="", slug="", body=""):
    """Auto-fix suggestions the client can apply with one click."""
    from django.utils.text import slugify

    out = {}
    if not slug and title:
        out["slug"] = slugify(title, allow_unicode=True)
    if not meta_description and body:
        # First ~155 characters of the plain body, trimmed at a word boundary.
        snippet = _strip_html(body)[:157].rsplit(" ", 1)[0]
        out["meta_description"] = snippet
    if title:
        out["meta_title"] = title[:60]
    return out
