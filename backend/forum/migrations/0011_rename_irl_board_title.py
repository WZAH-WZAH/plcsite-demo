from django.db import migrations


def rename_irl_board(apps, schema_editor):
    Board = apps.get_model('forum', 'Board')
    Board.objects.filter(slug='irl').update(title='三次元')


def noop_reverse(apps, schema_editor):
    # Data migration: no automatic reverse.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('forum', '0010_boardheroslide_post_views_count_and_more'),
    ]

    operations = [
        migrations.RunPython(rename_irl_board, reverse_code=noop_reverse),
    ]
