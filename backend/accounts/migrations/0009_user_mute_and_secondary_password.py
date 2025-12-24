from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_rename_accounts_st_user_id_2d7f53_idx_accounts_st_user_id_5d411e_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_muted',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='muted_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='mute_reason',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='user',
            name='secondary_password_hash',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='user',
            name='secondary_verified_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
