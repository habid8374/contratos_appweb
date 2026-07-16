import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Crea (o actualiza la contraseña de) un superusuario a partir de las '
        'variables de entorno DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_PASSWORD '
        'y DJANGO_SUPERUSER_EMAIL. Es idempotente: no falla si el usuario ya existe.'
    )

    def handle(self, *args, **options):
        username = os.getenv('DJANGO_SUPERUSER_USERNAME')
        password = os.getenv('DJANGO_SUPERUSER_PASSWORD')
        email = os.getenv('DJANGO_SUPERUSER_EMAIL', '')

        if not username or not password:
            self.stdout.write(
                'DJANGO_SUPERUSER_USERNAME/PASSWORD no definidos; se omite la creación.'
            )
            return

        User = get_user_model()
        user, creado = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )

        if creado:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superusuario '{username}' creado."))
        else:
            # Mantener acceso: asegurar flags y actualizar la contraseña.
            campos_actualizados = False
            if not user.is_superuser or not user.is_staff:
                user.is_superuser = True
                user.is_staff = True
                campos_actualizados = True
            if password:
                user.set_password(password)
                campos_actualizados = True
            if campos_actualizados:
                user.save()
            self.stdout.write(
                self.style.WARNING(f"Superusuario '{username}' ya existía; datos actualizados.")
            )
