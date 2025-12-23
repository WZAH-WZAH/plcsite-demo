from django.db import migrations


def add_site_boards(apps, schema_editor):
    Board = apps.get_model('forum', 'Board')

    # Keep these as normal boards; frontend will group them under “站务”.
    desired = [
        {'slug': 'feedback', 'title': '建议/反馈', 'description': '对站点的建议、问题反馈与需求收集。', 'sort_order': 900},
        {'slug': 'site-log', 'title': '站务日志', 'description': '站点公告、改动记录与运营日志。', 'sort_order': 910},
    ]

    for item in desired:
        Board.objects.update_or_create(
            slug=item['slug'],
            defaults={
                'title': item['title'],
                'description': item['description'],
                'sort_order': item['sort_order'],
                'is_active': True,
            },
        )


def noop(apps, schema_editor):
    # No destructive reverse migration.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('forum', '0011_rename_irl_board_title'),
    ]

    operations = [
        migrations.RunPython(add_site_boards, reverse_code=noop),
    ]
