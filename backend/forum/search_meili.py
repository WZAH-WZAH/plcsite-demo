"""Meilisearch integration for forum posts.

Why Meilisearch?
- Open source.
- Provides: autocomplete-ish suggestions (prefix search), highlight info, facet aggregation,
  typo tolerance (fuzzy-ish), fast ranking.

Important maintenance notes:
- This project has per-user visibility rules (published vs. author vs. staff).
  We keep all posts in the index and apply permission filters at query time.
- The index schema is intentionally minimal so we can iterate safely.
- If MEILI_URL is not configured, search endpoints will fall back to DB search.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.conf import settings


try:
    import meilisearch  # type: ignore
except Exception:  # pragma: no cover
    meilisearch = None


_ADV_TOKEN_RE = re.compile(r"^(?P<key>[a-zA-Z_]+):(?P<value>.+)$")


@dataclass(frozen=True)
class AdvancedQuery:
    """A lightweight 'advanced search' parsing result.

    We support a small, explicit subset to avoid unexpected behavior:
    - board:<slug>
    - author:<username>
    - status:published|pending|rejected
    - is:locked / is:pinned

    Everything else is treated as the free-text query.
    """

    text: str
    filters: List[str]


def meili_enabled() -> bool:
    """Returns True when Meilisearch is configured and importable."""

    return bool(getattr(settings, 'MEILI_URL', '')) and meilisearch is not None


def get_client():
    if not meili_enabled():
        raise RuntimeError('Meilisearch not configured.')
    return meilisearch.Client(settings.MEILI_URL, getattr(settings, 'MEILI_API_KEY', '') or None)


def get_posts_index():
    client = get_client()
    index_name = getattr(settings, 'MEILI_INDEX_POSTS', 'posts') or 'posts'
    return client.index(index_name)


def ensure_posts_index_settings() -> None:
    """Best-effort index settings.

    This is safe to call multiple times (idempotent-ish). It will be used by the
    reindex management command.
    """

    index = get_posts_index()

    # Searchable fields: title/body are the primary UX.
    index.update_searchable_attributes(['title', 'body'])

    # Filterable fields: required for aggregations and advanced filters.
    index.update_filterable_attributes(
        [
            'status',
            'board_id',
            'board_slug',
            'author_id',
            'author_username',
            'is_locked',
            'is_pinned',
        ]
    )

    # Sortable fields: used by 'latest' (and later for more ranking options).
    index.update_sortable_attributes(['created_at', 'updated_at'])

    # Displayed fields: what we return to clients.
    index.update_displayed_attributes(
        [
            'id',
            'title',
            'body',
            'status',
            'board_id',
            'board_slug',
            'author_id',
            'author_username',
            'is_locked',
            'is_pinned',
            'created_at',
            'updated_at',
        ]
    )

    # Chinese: Meilisearch does not do true word-segmentation by default.
    # We rely on its CJK-aware tokenization + prefix/typo tolerance for good UX.
    # For higher quality Chinese segmentation, consider OpenSearch/ES with IK analyzer.


def post_to_document(post) -> Dict[str, Any]:
    """Convert a Post model instance into an indexable document."""

    # NOTE: we store the raw markdown body; highlighting will work on this text.
    # If you later want cleaner snippets, add a separate 'body_plain' field.
    return {
        'id': int(post.id),
        'title': post.title or '',
        'body': post.body or '',
        'status': getattr(post, 'status', '') or '',
        'board_id': int(post.board_id) if getattr(post, 'board_id', None) else None,
        'board_slug': getattr(getattr(post, 'board', None), 'slug', '') or '',
        'author_id': int(post.author_id) if getattr(post, 'author_id', None) else None,
        'author_username': getattr(getattr(post, 'author', None), 'username', '') or '',
        'is_locked': bool(getattr(post, 'is_locked', False)),
        'is_pinned': bool(getattr(post, 'is_pinned', False)),
        'created_at': post.created_at.isoformat() if getattr(post, 'created_at', None) else None,
        'updated_at': post.updated_at.isoformat() if getattr(post, 'updated_at', None) else None,
    }


def parse_advanced_query(raw: str) -> AdvancedQuery:
    """Parse a user query string into free-text + Meilisearch filter expressions.

    Examples:
    - "PLC board:tools" -> text="PLC" filters=["board_slug = 'tools'"]
    - "author:alice status:published" -> text="" filters=[...]
    """

    raw = (raw or '').strip()
    if not raw:
        return AdvancedQuery(text='', filters=[])

    parts = [p for p in raw.split() if p.strip()]
    text_parts: List[str] = []
    filters: List[str] = []

    for part in parts:
        m = _ADV_TOKEN_RE.match(part)
        if not m:
            text_parts.append(part)
            continue

        key = (m.group('key') or '').lower()
        value = (m.group('value') or '').strip().strip('"').strip("'")
        if not value:
            continue

        if key == 'board':
            # slug
            filters.append(f"board_slug = '{value}'")
            continue
        if key == 'author':
            filters.append(f"author_username = '{value}'")
            continue
        if key == 'status':
            if value in {'published', 'pending', 'rejected'}:
                filters.append(f"status = '{value}'")
            continue
        if key == 'is':
            if value == 'locked':
                filters.append('is_locked = true')
            elif value == 'pinned':
                filters.append('is_pinned = true')
            continue

        # Unknown key => treat as normal text to avoid surprising behavior.
        text_parts.append(part)

    return AdvancedQuery(text=' '.join(text_parts).strip(), filters=filters)


def build_visibility_filter(*, user) -> Optional[str]:
    """Translate DRF visibility logic into a Meilisearch filter string."""

    if user and getattr(user, 'is_authenticated', False):
        if getattr(user, 'is_staff', False):
            return None
        # Normal authed users: published or own posts
        return f"(status = 'published') OR (author_id = {int(user.id)})"
    # Anonymous: published only
    return "status = 'published'"


def search_posts(*, user, raw_query: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """Search posts with highlight positions and facet aggregations."""

    index = get_posts_index()

    aq = parse_advanced_query(raw_query)
    visibility = build_visibility_filter(user=user)

    combined_filters: List[str] = []
    if visibility:
        combined_filters.append(f"({visibility})")
    combined_filters.extend(aq.filters)

    filter_expr = ' AND '.join(combined_filters) if combined_filters else None

    # facetsDistribution provides aggregation counts.
    res = index.search(
        aq.text or '',
        {
            'limit': int(max(1, min(limit, 50))),
            'offset': int(max(0, offset)),
            'filter': filter_expr,
            'attributesToRetrieve': [
                'id',
                'title',
                'body',
                'status',
                'board_id',
                'board_slug',
                'author_id',
                'author_username',
                'created_at',
                'updated_at',
            ],
            'showMatchesPosition': True,
            'facets': ['board_slug', 'author_username'],
        },
    )

    return {
        'engine': 'meili',
        'query': raw_query,
        'parsed': {'text': aq.text, 'filters': aq.filters, 'visibility': visibility},
        'hits': res.get('hits', []),
        'total': res.get('estimatedTotalHits', res.get('nbHits', 0)),
        'limit': res.get('limit', limit),
        'offset': res.get('offset', offset),
        'facets': res.get('facetDistribution', {}) or {},
    }


def suggest_posts(*, user, raw_query: str, limit: int = 8) -> Dict[str, Any]:
    """Return lightweight suggestions for topbar autocomplete."""

    index = get_posts_index()
    aq = parse_advanced_query(raw_query)
    visibility = build_visibility_filter(user=user)

    combined_filters: List[str] = []
    if visibility:
        combined_filters.append(f"({visibility})")
    combined_filters.extend(aq.filters)
    filter_expr = ' AND '.join(combined_filters) if combined_filters else None

    res = index.search(
        aq.text or '',
        {
            'limit': int(max(1, min(limit, 20))),
            'offset': 0,
            'filter': filter_expr,
            'attributesToRetrieve': ['id', 'title', 'board_slug', 'author_username'],
            'showMatchesPosition': True,
        },
    )

    return {
        'engine': 'meili',
        'query': raw_query,
        'hits': res.get('hits', []),
    }
