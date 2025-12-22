import bleach


# We only allow a tiny subset of raw HTML inside markdown.
# Markdown itself remains unchanged (e.g. **bold**, lists, headings).
# This is mainly to support:
# - our blank-line preservation placeholders (<br/>)
# - underline toolbar (<u>..</u>)
# - spoiler toolbar (<span class="spoiler">..</span>)
ALLOWED_TAGS = [
    'br',
    'u',
    'span',
]

ALLOWED_ATTRIBUTES = {
    'span': ['class'],
}


def sanitize_user_html_in_markdown(text: str) -> str:
    if text is None:
        return ''

    # Strip (not escape) disallowed tags for predictable rendering.
    cleaned = bleach.clean(
        str(text),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
    return cleaned
