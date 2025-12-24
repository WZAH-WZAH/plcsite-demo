from django.db import migrations


INTERNAL_BOARD_SLUGS = ['board_a', 'board_b']


def remove_internal_boards(apps, schema_editor):
    Board = apps.get_model('forum', 'Board')
    Post = apps.get_model('forum', 'Post')

    for slug in INTERNAL_BOARD_SLUGS:
        b = Board.objects.filter(slug=slug).first()
        if not b:
            continue

        # If anything references the board, do not hard-delete (PROTECT would fail).
        if Post.objects.filter(board_id=b.id).exists():
            b.is_active = False
            b.save(update_fields=['is_active'])
            continue

        try:
            b.delete()
        except Exception:
            # Safety net: never fail the migration for this cleanup.
            b.is_active = False
            b.save(update_fields=['is_active'])


class Migration(migrations.Migration):
    dependencies = [
        ('forum', '0013_add_blackroom_board'),
    ]

    operations = [
        migrations.RunPython(remove_internal_boards, migrations.RunPython.noop),
    ]
