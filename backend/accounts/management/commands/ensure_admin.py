from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create or update a staff admin account for notice board management.'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--password', required=True)
        parser.add_argument('--nickname', default='관리자')
        parser.add_argument('--email', default='admin@whatsub.local')

    def handle(self, *args, **options):
        username = options['username'].strip()
        password = options['password']
        nickname = (options['nickname'] or username)[:30]
        email = options['email'].strip()

        if not username:
            raise CommandError('username is required')
        if not password:
            raise CommandError('password is required')

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'nickname': nickname,
                'email': email,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        user.nickname = nickname or user.nickname or username[:30]
        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(f'{verb} admin user "{username}" (staff + superuser).'))
