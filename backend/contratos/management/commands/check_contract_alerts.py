
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from contratos.models import Contrato, AlertaContrato

class Command(BaseCommand):
    help = 'Revisa los contratos activos y envía alertas de vencimiento por correo electrónico.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Iniciando revisión de alertas de vencimiento para: {date.today()}"))
        contratos_con_alerta = Contrato.objects.filter(
            estado=Contrato.Estado.ACTIVO,
            alerta__isnull=False,
            alerta__activa=True
        ).select_related('administradora', 'alerta')
        contratos_notificados = 0
        for contrato in contratos_con_alerta:
            alerta = contrato.alerta
            fecha_alerta_calculada = contrato.fecha_fin - timedelta(days=alerta.dias_previos)
            if date.today() == fecha_alerta_calculada and alerta.ultima_notificacion_enviada != date.today():
                self.stdout.write(self.style.WARNING(f"¡ALERTA! El contrato '{contrato.numero_contrato}' requiere notificación."))
                self.enviar_correo_alerta(contrato, alerta)
                alerta.ultima_notificacion_enviada = date.today()
                alerta.save()
                contratos_notificados += 1
        self.stdout.write(self.style.SUCCESS(f"Revisión finalizada. Se enviaron {contratos_notificados} notificaciones."))

    def enviar_correo_alerta(self, contrato: Contrato, alerta: AlertaContrato):
        dias_restantes = (contrato.fecha_fin - date.today()).days
        asunto = f"ALERTA CRÍTICA: Vencimiento de Contrato - {contrato.administradora.nombre} ({dias_restantes} días restantes)"
        context = {
            'contrato': contrato,
            'dias_restantes': dias_restantes,
            'link_gestion': f"http://localhost:4200/contratos/{contrato.id}"
        }
        html_message = f\"\"\"
        <div style="font-family: Arial, sans-serif; border: 2px solid #D32F2F; padding: 20px;">
            <h1 style="color: #D32F2F;">ALERTA DE VENCIMIENTO DE CONTRATO</h1>
            <p>Este es un aviso para informar que el contrato con <strong>{contrato.administradora.nombre}</strong> (N° {contrato.numero_contrato}) vence en <strong>{dias_restantes} días</strong>.</p>
            <a href="{context['link_gestion']}" style="background-color: #1976D2; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px;">Gestionar Contrato</a>
        </div>
        \"\"\"
        send_mail(
            subject=asunto,
            message=f"El contrato {contrato.numero_contrato} vence en {dias_restantes} días.",
            from_email='noreply@clinicacentro.com',
            recipient_list=['equipo.contratacion@example.com'],
            html_message=html_message,
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Correo enviado para el contrato {contrato.numero_contrato}."))
