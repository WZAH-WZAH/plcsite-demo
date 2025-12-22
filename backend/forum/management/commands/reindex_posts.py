"""Reindex forum posts into Meilisearch.

Usage:
  python manage.py reindex_posts

Notes:
- This is intentionally a manual command (not automatic hooks) so that devs can
  bootstrap search quickly.
- In production you may want:
  - a background job / queue
  - incremental updates on post create/update/moderation
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from forum.models import Post
from forum.search_meili import ensure_posts_index_settings, get_posts_index, meili_enabled, post_to_document


class Command(BaseCommand):
    help = 'Reindex posts into Meilisearch.'

    def handle(self, *args, **options):
        if not meili_enabled():
            self.stdout.write(self.style.ERROR('MEILI_URL not configured or meilisearch package missing.'))
            self.stdout.write('Set MEILI_URL/MEILI_API_KEY in backend/.env and run again.')
            return

        ensure_posts_index_settings()
        index = get_posts_index()

        qs = Post.objects.select_related('board', 'author').all().order_by('id')
        docs = [post_to_document(p) for p in qs]

        # Meilisearch can accept batch documents. For large data, chunking is advised.
        task = index.add_documents(docs, primary_key='id')
        self.stdout.write(self.style.SUCCESS(f'Indexed {len(docs)} posts. task={task}'))
