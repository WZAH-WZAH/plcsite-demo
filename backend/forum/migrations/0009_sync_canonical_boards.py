from django.db import migrations


CANONICAL_BOARDS = [
    # Notes:
    # - 这些是“可发帖”的实际板块（对应发帖页下拉框）。
    # - “首页/最近更新”属于导航入口，不作为 Board 记录。
    ("games", "游戏"),
    ("mmd", "MMD/里番"),
    ("irl", "IRL/三次元"),
    ("tech", "技术交流"),
    ("daily", "日常分享"),
    ("announcements", "公告"),
]


def sync_boards(apps, schema_editor):
    Board = apps.get_model("forum", "Board")
    Post = apps.get_model("forum", "Post")

    slug_to_order = {slug: idx * 10 for idx, (slug, _title) in enumerate(CANONICAL_BOARDS, start=1)}

    # 1) Ensure canonical boards exist and are active + ordered.
    for slug, title in CANONICAL_BOARDS:
        obj = Board.objects.filter(slug=slug).first()
        if obj is None:
            Board.objects.create(
                slug=slug,
                title=title,
                description="",
                sort_order=slug_to_order[slug],
                is_active=True,
            )
        else:
            changed = False
            if obj.title != title:
                obj.title = title
                changed = True
            if obj.sort_order != slug_to_order[slug]:
                obj.sort_order = slug_to_order[slug]
                changed = True
            if not obj.is_active:
                obj.is_active = True
                changed = True
            if changed:
                obj.save(update_fields=["title", "sort_order", "is_active"])

    # 2) Remove/deactivate non-canonical boards.
    canonical_slugs = set(slug_to_order.keys())
    extras = Board.objects.exclude(slug__in=canonical_slugs)
    for b in extras:
        has_posts = Post.objects.filter(board_id=b.id).exists()
        if not has_posts:
            # Safe physical delete (no PROTECT FK references).
            b.delete()
        else:
            # PROTECT prevents deletion; hide it from public lists.
            if b.is_active:
                b.is_active = False
                b.save(update_fields=["is_active"])


def noop_reverse(apps, schema_editor):
    # Data migration: no automatic reverse.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("forum", "0008_remove_homeheroslide_forum_homeh_post_id_7c4333_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(sync_boards, reverse_code=noop_reverse),
    ]
