from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


@dataclass(frozen=True)
class _SeedUserSpec:
    username: str
    nickname: str
    is_staff: bool = False
    is_superuser: bool = False
    email: str = ''


DEFAULT_TEST_USERS: list[_SeedUserSpec] = [
    _SeedUserSpec(username='@admin_perfectlife', nickname='管理员', is_staff=True, is_superuser=True),
    _SeedUserSpec(username='@mod', nickname='版主', is_staff=True, is_superuser=False),
    _SeedUserSpec(username='@test1', nickname='测试号1'),
    _SeedUserSpec(username='@test2', nickname='测试号2'),
]


def _normalize_handle(v: str) -> str:
    s = (v or '').strip().lower()
    if not s.startswith('@'):
        s = '@' + s
    return s


def _make_pid(user_id: int) -> str:
    return str(int(user_id)).zfill(8)


class Command(BaseCommand):
    help = 'Create/reset demo test users and print their nickname/username/PID/password.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default='PlcTest123',
            help='Password to set for all seeded users (default: PlcTest123). Must pass password validators.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without changing the database.',
        )

    def handle(self, *args, **options):
        password: str = options['password']
        dry_run: bool = bool(options['dry_run'])

        # get_user_model() is typed as AbstractUser; our project uses a custom
        # accounts.User with extra fields (pid/nickname). Keep typing flexible.
        User: Any = get_user_model()

        rows: list[dict[str, str]] = []
        created = 0
        updated = 0

        for spec in DEFAULT_TEST_USERS:
            username = _normalize_handle(spec.username)
            nickname = (spec.nickname or '').strip()[:20]

            user: Any = User.objects.filter(username__iexact=username).first()
            is_new = user is None
            if user is None:
                user = User(username=username)

            # Update core fields
            user.username = username
            user.nickname = nickname
            if spec.email:
                user.email = spec.email

            user.is_active = True
            user.is_staff = bool(spec.is_staff or spec.is_superuser)
            user.is_superuser = bool(spec.is_superuser)

            if not dry_run:
                if is_new:
                    # set password before save so hash exists
                    user.set_password(password)
                    user.save()
                else:
                    user.save(update_fields=['username', 'nickname', 'email', 'is_active', 'is_staff', 'is_superuser'])
                    user.set_password(password)
                    user.save(update_fields=['password'])

                # Ensure pid exists
                if not getattr(user, 'pid', None):
                    user.pid = _make_pid(user.id)
                    user.save(update_fields=['pid'])

            pid = getattr(user, 'pid', None) or ('(new)' if dry_run else '')

            rows.append(
                {
                    'role': 'superuser' if spec.is_superuser else ('staff' if spec.is_staff else 'user'),
                    'nickname': nickname,
                    'username': username,
                    'pid': str(pid),
                    'password': password,
                }
            )

            if is_new:
                created += 1
            else:
                updated += 1

        # Print summary
        self.stdout.write(self.style.SUCCESS(f'Test users ready. created={created}, updated={updated}, dry_run={dry_run}'))
        self.stdout.write('')

        # Pretty print
        headers = ['role', 'nickname', 'username', 'pid', 'password']
        col_widths = {h: max(len(h), *(len(str(r.get(h, ''))) for r in rows)) for h in headers}

        def fmt_row(r: dict[str, str]) -> str:
            return '  '.join(str(r.get(h, '')).ljust(col_widths[h]) for h in headers)

        self.stdout.write(fmt_row({h: h for h in headers}))
        self.stdout.write('  '.join('-' * col_widths[h] for h in headers))
        for r in rows:
            self.stdout.write(fmt_row(r))
