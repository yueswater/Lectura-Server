import logging
import os
import re
import urllib.parse
from datetime import datetime

import markdown
import yaml
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from letters.models import EmailTemplate, Letter
from letters.tasks import send_letter_task
from weasyprint import HTML

logger = logging.getLogger("weasyprint")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def latex_to_svg_image(text):
    if not text:
        return ""
    pattern_block = r"\$\$(.*?)\$\$"

    def replace_block(match):
        encoded_code = urllib.parse.quote(match.group(1).strip())
        return f'<div class="math-block"><img src="https://latex.codecogs.com/svg.latex?{encoded_code}" /></div>'

    text = re.sub(pattern_block, replace_block, text, flags=re.DOTALL)
    pattern_inline = r"\$(.*?)\$"

    def replace_inline(match):
        encoded_code = urllib.parse.quote(match.group(1).strip())
        return f'<img class="math-inline" src="https://latex.codecogs.com/svg.latex?{encoded_code}" />'

    return re.sub(pattern_inline, replace_inline, text)


def get_recursive_sections(handout, parent=None):
    ordered_sections = []
    sections = handout.sections.filter(parent=parent).order_by("order")
    for section in sections:
        ordered_sections.append(section)
        ordered_sections.extend(get_recursive_sections(handout, parent=section))
    return ordered_sections


def generate_handout_pdf(handout):
    user_config = handout.yaml_config
    if isinstance(user_config, str):
        try:
            user_config = yaml.safe_load(user_config) or {}
        except Exception:
            user_config = {}
    elif not isinstance(user_config, dict):
        user_config = {}

    theme_defaults = {
        "nordic_dark": {"h1": "#2E3440", "h2": "#3B4252", "h3": "#434C5E", "h4": "#4C566A"},
        "modern_blue": {"h1": "#003366", "h2": "#0055A4", "h3": "#0072CE", "h4": "#00A3E0"},
        "academic": {"h1": "#1A1A1A", "h2": "#333333", "h3": "#4D4D4D", "h4": "#666666"},
    }

    font_map = {
        "sans": '"Montserrat", "Noto Sans TC", sans-serif',
        "serif": '"Playfair Display", "Noto Serif TC", serif',
        "mono": '"JetBrains Mono", monospace',
    }

    page_format = {
        "en": "'Page ' counter(page) ' of ' counter(pages)",
        "zh_TW": "'第 ' counter(page) ' 頁，共 ' counter(pages) ' 頁'",
        "zh_CN": "'第 ' counter(page) ' 页，共 ' counter(pages) ' 页'",
        "th": "'หน้า ' counter(page) ' จาก ' counter(pages)",
    }

    toc_titles = {
        "en": "Contents",
        "zh_TW": "目錄",
        "zh_CN": "目录",
        "th": "สารบัญ",
    }

    raw_lang = user_config.get("language", "en")
    lang = raw_lang.replace("_", "-").lower()
    if lang == "zh-tw":
        lang = "zh-hant"
    elif lang == "zh-cn":
        lang = "zh-hans"
    selected_page_content = page_format.get(lang, page_format["en"])
    selected_toc_title = toc_titles.get(lang, toc_titles["en"])
    page_pos = user_config.get("page_number_pos", "bottom-right")

    display_subtitle = handout.subtitle.replace("|", "<br />") if handout.subtitle else ""

    selected_theme = user_config.get("theme", "nordic_dark")
    base_font_key = user_config.get("font_style", "sans")
    use_custom = user_config.get("use_custom_typography", False)
    raw_typo = user_config.get("typography", {})
    indent_mode = user_config.get("indent_mode", "none")

    typography = {}
    for level in ["h1", "h2", "h3", "h4"]:
        if use_custom and level in raw_typo:
            level_data = raw_typo[level]
            typography[level] = {
                "color": level_data.get(
                    "color", theme_defaults.get(selected_theme, theme_defaults["nordic_dark"])[level]
                ),
                "font_family": font_map.get(level_data.get("font", base_font_key), font_map[base_font_key]),
            }
        else:
            typography[level] = {
                "color": theme_defaults.get(selected_theme, theme_defaults["nordic_dark"])[level],
                "font_family": font_map.get(base_font_key, font_map["sans"]),
            }

    config = {
        "author": user_config.get("author", ""),
        "institution": user_config.get("institution", ""),
        "date": user_config.get("date", datetime.now().strftime("%B %d, %Y")),
        "base_font": font_map.get(base_font_key, font_map["sans"]),
        "indent_mode": indent_mode,
        "page_number_content": selected_page_content,
        "page_number_pos": page_pos,
        "toc_title": selected_toc_title,
    }

    sections_data = []
    md_extensions = ["extra", "codehilite", "toc", "attr_list", "tables"]
    md_configs = {"codehilite": {"css_class": "highlight", "linenums": False, "guess_lang": True}}

    all_ordered_sections = get_recursive_sections(handout)
    for section in all_ordered_sections:
        content_with_latex = latex_to_svg_image(section.content or "")
        rendered_html = markdown.markdown(content_with_latex, extensions=md_extensions, extension_configs=md_configs)

        if settings.MEDIA_URL in rendered_html:
            rendered_html = rendered_html.replace(settings.MEDIA_URL, f"file://{settings.MEDIA_ROOT}/")

        sections_data.append({"title": section.title, "html_body": rendered_html, "level": section.level})

    actual_static_path = settings.BASE_DIR / "static"
    css_file_path = os.path.join(actual_static_path, "css/pdf/handout_style.css")

    try:
        with open(css_file_path, "r", encoding="utf-8") as f:
            custom_css = f.read()
    except Exception as e:
        logger.warning(f"Failed to load CSS file: {e}")
        custom_css = ""

    context = {
        "title": handout.title,
        "subtitle": display_subtitle,
        "description": handout.description,
        "sections": sections_data,
        "config": config,
        "typography": typography,
        "static_root": actual_static_path,
        "custom_css": custom_css,
    }

    html_string = render_to_string("pdf/handout_template.html", context)

    pdf_content = HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf()
    handout.file_size = len(pdf_content)
    handout.last_downloaded_at = timezone.now()
    handout.save(update_fields=["file_size", "last_downloaded_at"])
    return pdf_content


def trigger_storage_email(user, usage, limit, level):
    if user.last_storage_warning_level >= level:
        return

    used_mb = f"{usage / (1024 * 1024):.2f} MB"
    limit_mb = f"{limit / (1024 * 1024):.2f} MB"
    template_name = f"storage_warning_{level}"

    language_aliases = {
        "zh_TW": ["zh-hant", "zh-tw", "zh_TW"],
        "zh_CN": ["zh-hans", "zh-cn", "zh_CN"],
        "th": ["th"],
        "en": ["en", "en-us"],
    }

    user_lang = getattr(user, "language", "zh_TW")

    search_langs = language_aliases.get(user_lang, []) + language_aliases["zh_TW"] + language_aliases["en"]

    template = None

    try:
        for lang_code in search_langs:
            template = EmailTemplate.objects.filter(name=template_name, language=lang_code).first()
            if template:
                break

        if not template:
            print(f"DEBUG: No template found for {template_name} even after aliases.")
            return

        letter = Letter.objects.create(
            template=template,
            recipient_email=user.email,
            context={
                "username": user.username,
                "used_storage": used_mb,
                "storage_limit": limit_mb,
                "percentage": f"{int((usage / limit) * 100)}%",
                "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
            },
        )

        send_letter_task.delay(letter.id)
        user.last_storage_warning_level = level
        user.save(update_fields=["last_storage_warning_level"])
        print(f"DEBUG: Successfully sent {template.language} email to {user.email}")

    except Exception as e:
        print(f"DEBUG: Email trigger failed: {str(e)}")
