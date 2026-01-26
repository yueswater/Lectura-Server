THEME_DEFAULTS = {
    "nordic_dark": {"h1": "#2E3440", "h2": "#3B4252", "h3": "#434C5E", "h4": "#4C566A"},
    "modern_blue": {"h1": "#003366", "h2": "#0055A4", "h3": "#0072CE", "h4": "#00A3E0"},
    "academic": {"h1": "#1A1A1A", "h2": "#333333", "h3": "#4D4D4D", "h4": "#666666"},
}

FONT_MAP = {
    "sans": '"Montserrat", "Noto Sans TC", "Noto Sans Thai", sans-serif',
    "serif": '"Playfair Display", "Noto Serif TC", "Sarabun", serif',
    "mono": '"JetBrains Mono", "Noto Sans Thai Looped", monospace',
}

PAGE_FORMATS = {
    "en": "'Page ' counter(page) ' of ' counter(pages)",
    "zh_TW": "'第 ' counter(page) ' 頁，共 ' counter(pages) ' 頁'",
    "zh_CN": "'第 ' counter(page) ' 页，共 ' counter(pages) ' 页'",
    "th": "'หน้า ' counter(page) ' จาก ' counter(pages)",
}

TOC_TITLES = {
    "en": "Contents",
    "zh_TW": "目錄",
    "zh_CN": "目錄",
    "th": "สารบัญ",
}

FIGURE_LABELS = {"en": "Figure", "zh_TW": "圖", "zh_CN": "图", "th": "รูป"}

ADMONITION_ICONS = {
    "info": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="#3b82f6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>'
    ),
    "warning": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="#f59e0b" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
        '<path d="M12 9v4"/><path d="M12 17h.01"/></svg>'
    ),
    "danger": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="#ef4444" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>'
        '<line x1="9" y1="9" x2="15" y2="15"/></svg>'
    ),
    "success": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
    ),
    "tip": (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        'stroke="#8b5cf6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .5 2.2 1.5 3.1.8.9 '
        '1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>'
    ),
}


def get_language_config(raw_lang):
    """Normalize language and return related strings."""
    lang = raw_lang.replace("_", "-").lower()

    if lang == "zh-tw":
        lang = "zh-hant"
    elif lang == "zh-cn":
        lang = "zh-hans"

    return {
        "lang": lang,
        "page_content": PAGE_FORMATS.get(raw_lang, PAGE_FORMATS["en"]),
        "toc_title": TOC_TITLES.get(raw_lang, TOC_TITLES["en"]),
        "fig_label": FIGURE_LABELS.get(raw_lang, FIGURE_LABELS["en"]),
    }
