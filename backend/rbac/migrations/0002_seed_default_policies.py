from django.db import migrations


def seed_default_policies(apps, schema_editor):
    CasbinRule = apps.get_model('rbac', 'CasbinRule')

    policies = [
        # Keep current behavior: any is_staff can use current admin APIs by default.
        ('role:staff', '*', 'admin.users', 'read'),
        ('role:staff', '*', 'admin.users', 'ban'),
        ('role:staff', '*', 'admin.users', 'unban'),
        ('role:staff', '*', 'admin.users', 'mute'),
        ('role:staff', '*', 'admin.users', 'unmute'),
        ('role:staff', '*', 'admin.users', 'grant_staff'),
        ('role:staff', '*', 'admin.users', 'revoke_staff'),
        ('role:staff', '*', 'admin.users', 'board_perms'),
        ('role:staff', '*', 'admin.audit', 'read'),
    ]

    CasbinRule.objects.bulk_create(
        [
            CasbinRule(ptype='p', v0=sub, v1=dom, v2=obj, v3=act)
            for (sub, dom, obj, act) in policies
        ],
        ignore_conflicts=True,
    )


def unseed_default_policies(apps, schema_editor):
    CasbinRule = apps.get_model('rbac', 'CasbinRule')
    CasbinRule.objects.filter(ptype='p', v0='role:staff', v2__in=['admin.users', 'admin.audit']).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('rbac', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_default_policies, unseed_default_policies),
    ]
