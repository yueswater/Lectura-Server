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

from .theme import ADMONITION_ICONS, FONT_MAP, THEME_DEFAULTS, get_language_config

logger = logging.getLogger("weasyprint")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def inject_admonition_icons(html):
    for alert_type, svg in ADMONITION_ICONS.items():
        pattern = rf"(<div [^>]*class=[^>]*admonition {alert_type}[^>]*>\s*<p [^>]*class=[^>]*admonition-title[^>]*>)"
        replacement = rf'\1<span class="admonition-icon">{svg}</span>'
        html = re.sub(pattern, replacement, html)
    return html


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

    lang_cfg = get_language_config(user_config.get("language", "en"))
    display_subtitle = handout.subtitle.replace("|", "<br />") if handout.subtitle else ""
    selected_theme = user_config.get("theme", "nordic_dark")
    base_font_key = user_config.get("font_style", "sans")
    use_custom = user_config.get("use_custom_typography", False)
    raw_typo = user_config.get("typography", {})
    indent_mode = user_config.get("indent_mode", "none")

    typography = {}
    current_theme_colors = THEME_DEFAULTS.get(selected_theme, THEME_DEFAULTS["nordic_dark"])

    for level in ["h1", "h2", "h3", "h4"]:
        if use_custom and level in raw_typo:
            level_data = raw_typo[level]
            typography[level] = {
                "color": level_data.get("color", current_theme_colors[level]),
                "font_family": FONT_MAP.get(level_data.get("font", base_font_key), FONT_MAP[base_font_key]),
            }
        else:
            typography[level] = {
                "color": current_theme_colors[level],
                "font_family": FONT_MAP.get(base_font_key, FONT_MAP["sans"]),
            }

    config = {
        "author": user_config.get("author", ""),
        "institution": user_config.get("institution", ""),
        "date": user_config.get("date", datetime.now().strftime("%B %d, %Y")),
        "base_font": FONT_MAP.get(base_font_key, FONT_MAP["sans"]),
        "indent_mode": indent_mode,
        "page_number_content": lang_cfg["page_content"],
        "page_number_pos": user_config.get("page_number_pos", "bottom-right"),
        "toc_title": lang_cfg["toc_title"],
    }

    sections_data = []
    md_extensions = [
        "extra",
        "codehilite",
        "toc",
        "attr_list",
        "tables",
        "markdown_captions",
        "pymdownx.blocks.admonition",
    ]
    md_configs = {"codehilite": {"css_class": "highlight", "linenums": False, "guess_lang": True}}

    all_ordered_sections = get_recursive_sections(handout)
    for section in all_ordered_sections:
        content_with_latex = latex_to_svg_image(section.content or "")
        rendered_html = markdown.markdown(content_with_latex, extensions=md_extensions, extension_configs=md_configs)

        logger.debug(f"DEBUG HTML for {section.title}: {rendered_html}")

        rendered_html = inject_admonition_icons(rendered_html)

        if "http://localhost:8000/media/" in rendered_html:
            rendered_html = rendered_html.replace("http://localhost:8000/media/", f"file://{settings.MEDIA_ROOT}/")
        elif rendered_html.find('src="' + settings.MEDIA_URL) != -1:
            rendered_html = rendered_html.replace('src="' + settings.MEDIA_URL, f'src="file://{settings.MEDIA_ROOT}/')

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
        "fig_label": lang_cfg["fig_label"],
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

    except Exception as e:
        print(f"DEBUG: Email trigger failed: {str(e)}")
