from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Send a test email to verify SMTP (AWS SES) connectivity.'

    def add_arguments(self, parser):
        parser.add_argument('email', help='Recipient email address')

    def handle(self, *args, **options):
        recipient = str(options['email'] or '').strip()
        if not recipient:
            raise CommandError('Recipient email is required.')

        from_email = (
            getattr(settings, 'DEFAULT_FROM_EMAIL', None)
            or getattr(settings, 'SERVER_EMAIL', None)
            or getattr(settings, 'EMAIL_HOST_USER', None)
            or ''
        )
        if not from_email:
            raise CommandError('DEFAULT_FROM_EMAIL/SERVER_EMAIL is not configured.')

        subject = 'Test Email (AWS SES SMTP)'
        message = 'This is a test email sent by Django management command: test_email.'

        try:
            sent = send_mail(subject, message, from_email, [recipient], fail_silently=False)
        except Exception as exc:
            raise CommandError(f'Failed to send email: {exc}')

        if sent:
            self.stdout.write(self.style.SUCCESS(f'Email sent successfully to {recipient}'))
        else:
            raise CommandError('send_mail returned 0 (no email sent).')
