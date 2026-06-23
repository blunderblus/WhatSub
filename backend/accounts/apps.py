from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Site 도메인은 migrate 후 manage.py shell 등에서 한 번 맞춰 주세요.
        pass
