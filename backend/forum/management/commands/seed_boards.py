from django.core.management.base import BaseCommand

from forum.models import Board


class Command(BaseCommand):
    help = 'Create default boards if they do not exist.'

    def handle(self, *args, **options):
        defaults = [
            ('games', '游戏'),
            ('comics', '漫画'),
            ('cos', 'cos'),
            ('daily', '日常'),
            ('sage', '贤者时刻'),
            ('tech', '技术交流'),
        ]

        created = 0
        for order, (slug, title) in enumerate(defaults, start=1):
            obj, was_created = Board.objects.get_or_create(
                slug=slug,
                defaults={'title': title, 'sort_order': order, 'is_active': True},
            )
            if was_created:
                created += 1
            else:
                # Keep title/order aligned, but don't overwrite description.
                changed = False
                if obj.title != title:
                    obj.title = title
                    changed = True
                if obj.sort_order != order:
                    obj.sort_order = order
                    changed = True
                if changed:
                    obj.save(update_fields=['title', 'sort_order'])

        self.stdout.write(self.style.SUCCESS(f'Boards ready. Created: {created}'))