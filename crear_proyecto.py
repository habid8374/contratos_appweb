import os
import subprocess

# --- CONTENIDO DE LOS ARCHIVOS ---

# --- BACKEND: DJANGO ---

MODELS_PY_CONTENT = r"""
import os
from datetime import date, timedelta
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def anexo_upload_path(instance, filename):
    # Guarda el archivo en una carpeta con el ID del contrato para mantener el orden
    return f'contratos/{instance.contrato.id}/anexos/{filename}'

class Administradora(models.Model):
    nombre = models.CharField(max_length=255, unique=True, db_index=True)
    nit = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.nombre

class Contrato(models.Model):
    class Modalidad(models.TextChoices):
        EVENTO = 'EV', _('Evento')
        CAPITACION = 'CAP', _('Capitación')
        PGP = 'PGP', _('Paquete de Gestión Global (PGP)')

    class Estado(models.TextChoices):
        ACTIVO = 'ACT', _('Activo')
        INACTIVO = 'INA', _('Inactivo')

    numero_contrato = models.CharField(max_length=100, unique=True, db_index=True)
    administradora = models.ForeignKey(Administradora, on_delete=models.PROTECT, related_name='contratos')
    modalidad = models.CharField(max_length=3, choices=Modalidad.choices, default=Modalidad.EVENTO)
    objeto = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    valor_total = models.DecimalField(max_digits=19, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=3, choices=Estado.choices, default=Estado.ACTIVO)

    def __str__(self):
        return f"{self.numero_contrato} - {self.administradora.nombre}"

class AlertaContrato(models.Model):
    contrato = models.OneToOneField(Contrato, on_delete=models.CASCADE, related_name='alerta')
    dias_previos = models.PositiveIntegerField(default=90, help_text="Días previos para generar la alerta antes del vencimiento.")
    activa = models.BooleanField(default=True)
    ultima_notificacion_enviada = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"Alerta para {self.contrato.numero_contrato} a {self.dias_previos} días."

class AnexoTarifario(models.Model):
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='anexos')
    nombre_anexo = models.CharField(max_length=255)
    archivo_excel = models.FileField(upload_to=anexo_upload_path)
    fecha_carga = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre_anexo} ({self.contrato.numero_contrato})"

class DetalleTarifa(models.Model):
    class TipoTecnologia(models.TextChoices):
        PROCEDIMIENTO = 'P', _('Procedimiento')
        MEDICAMENTO = 'M', _('Medicamento')
        INSUMO = 'I', _('Insumo')

    anexo_origen = models.ForeignKey(AnexoTarifario, on_delete=models.CASCADE, related_name='detalles')
    codigo_cups = models.CharField(max_length=20, db_index=True)
    descripcion = models.CharField(max_length=500)
    tipo_tecnologia = models.CharField(max_length=1, choices=TipoTecnologia.choices)
    esta_incluido = models.BooleanField(default=True)
    manual_referencia = models.CharField(max_length=50)
    tarifa_base = models.DecimalField(max_digits=14, decimal_places=2)
    porcentaje_pactado = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    valor_final = models.DecimalField(max_digits=14, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        self.valor_final = self.tarifa_base * (1 + self.porcentaje_pactado / 100)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo_cups} - {self.descripcion}"

    class Meta:
        unique_together = ('anexo_origen', 'codigo_cups')
"""

EXCEL_PROCESSOR_PY_CONTENT = r"""
import pandas as pd
from django.db import transaction
from django.core.exceptions import ValidationError
from contratos.models import DetalleTarifa, AnexoTarifario

class ExcelTarifarioProcessor:
    COLUMN_MAP = {
        'codigo_cups': ['codigo_cups', 'codigo', 'cups'],
        'descripcion': ['descripcion', 'descripcion_procedimiento', 'nombre_tecnologia'],
        'tipo_tecnologia': ['tipo_tecnologia', 'tipo'],
        'esta_incluido': ['esta_incluido', 'incluido', 'incluido_pos'],
        'manual_referencia': ['manual_referencia', 'manual'],
        'tarifa_base': ['tarifa_base', 'valor_base', 'tarifa'],
        'porcentaje_pactado': ['porcentaje_pactado', 'porcentaje', '%_pactado'],
    }
    TIPO_TECNOLOGIA_MAP = {'procedimiento': 'P', 'medicamento': 'M', 'insumo': 'I'}

    def __init__(self, anexo_instance: AnexoTarifario):
        if not anexo_instance or not anexo_instance.archivo_excel:
            raise ValueError("La instancia de AnexoTarifario y su archivo no pueden ser nulos.")
        self.anexo = anexo_instance
        self.file_path = anexo_instance.archivo_excel.path

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        df.columns = df.columns.str.lower().str.strip()
        for model_field, possible_names in self.COLUMN_MAP.items():
            for name in possible_names:
                if name in df.columns:
                    df.rename(columns={name: model_field}, inplace=True)
                    break
        required_cols = ['codigo_cups', 'descripcion', 'tarifa_base']
        for col in required_cols:
            if col not in df.columns:
                raise ValidationError(f"La columna esencial '{col}' no se encontró en el archivo Excel.")
        return df

    def process(self):
        try:
            df = pd.read_excel(self.file_path)
            df = self._normalize_dataframe(df)
        except Exception as e:
            raise IOError(f"No se pudo leer o procesar el archivo Excel: {e}")

        detalles_a_crear = []
        for index, row in df.iterrows():
            tipo_tecnologia_str = str(row.get('tipo_tecnologia', 'procedimiento')).lower()
            tipo_tecnologia = self.TIPO_TECNOLOGIA_MAP.get(tipo_tecnologia_str, 'P')
            incluido_val = str(row.get('esta_incluido', 'True')).lower()
            esta_incluido = incluido_val in ['true', 'si', '1', 'incluido']
            detalle = DetalleTarifa(
                anexo_origen=self.anexo,
                codigo_cups=str(row['codigo_cups']),
                descripcion=str(row['descripcion']),
                tipo_tecnologia=tipo_tecnologia,
                esta_incluido=esta_incluido,
                manual_referencia=str(row.get('manual_referencia', 'Propio')),
                tarifa_base=pd.to_numeric(row['tarifa_base'], errors='coerce') or 0,
                porcentaje_pactado=pd.to_numeric(row.get('porcentaje_pactado', 0), errors='coerce') or 0,
            )
            detalles_a_crear.append(detalle)

        if not detalles_a_crear: return 0
        with transaction.atomic():
            DetalleTarifa.objects.filter(anexo_origen=self.anexo).delete()
            DetalleTarifa.objects.bulk_create(detalles_a_crear, batch_size=1000)
        return len(detalles_a_crear)
"""

CHECK_ALERTS_PY_CONTENT = r"""
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
"""

SERIALIZERS_PY_CONTENT = r"""
from rest_framework import serializers
from .models import Contrato, Administradora

class AdministradoraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administradora
        fields = ['nombre', 'nit']

class ContratoBusquedaSerializer(serializers.ModelSerializer):
    administradora = AdministradoraSerializer(read_only=True)
    regimen_estimado = serializers.SerializerMethodField()

    class Meta:
        model = Contrato
        fields = ['id', 'numero_contrato', 'administradora', 'modalidad', 'fecha_fin', 'estado', 'regimen_estimado']

    def get_regimen_estimado(self, obj):
        nombre_admin = obj.administradora.nombre.lower()
        if 'subsidiado' in nombre_admin: return 'Subsidiado'
        if 'contributivo' in nombre_admin: return 'Contributivo'
        if obj.modalidad == 'EV': return 'Evento'
        return 'No identificado'
"""

VIEWS_PY_CONTENT = r"""
from rest_framework.generics import ListAPIView
from django.db.models import Q
from .models import Contrato
from .serializers import ContratoBusquedaSerializer

class BuscadorContratoView(ListAPIView):
    serializer_class = ContratoBusquedaSerializer
    # permission_classes = [IsAuthenticated] # Descomentar cuando JWT esté listo

    def get_queryset(self):
        query = self.request.query_params.get('q', None)
        if query:
            return Contrato.objects.select_related('administradora').filter(
                Q(administradora__nombre__icontains=query) |
                Q(numero_contrato__icontains=query)
            ).filter(estado=Contrato.Estado.ACTIVO).order_by('administradora__nombre')
        return Contrato.objects.none()
"""

URLS_PY_CONTENT = r"""
from django.urls import path
from .views import BuscadorContratoView

urlpatterns = [
    path('contratos/buscar/', BuscadorContratoView.as_view(), name='buscar-contratos'),
]
"""

# --- FRONTEND: ANGULAR ---

SEARCH_BAR_TS_CONTENT = r"""
import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormControl } from '@angular/forms';
import { Observable, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, takeUntil, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
// Asumimos que tienes un servicio ApiService y un modelo Contrato
// import { ApiService } from '../../core/services/api.service';
// import { Contrato } from '../../shared/models/contrato.model';

@Component({
  selector: 'app-search-bar',
  templateUrl: './search-bar.component.html',
  styleUrls: ['./search-bar.component.scss']
})
export class SearchBarComponent implements OnInit, OnDestroy {
  searchControl = new FormControl('');
  // resultados$: Observable<Contrato[]>; // Descomentar cuando el servicio esté listo
  isLoading = false;
  private destroy$ = new Subject<void>();

  constructor(private router: Router) {} // Inyectar ApiService aquí

  ngOnInit(): void {
    // this.resultados$ = this.searchControl.valueChanges.pipe(
    //   takeUntil(this.destroy$),
    //   debounceTime(300),
    //   distinctUntilChanged(),
    //   tap(() => this.isLoading = true),
    //   switchMap(termino => this.apiService.buscarContratos(termino || '')),
    //   tap(() => this.isLoading = false)
    // );
  }

  seleccionarContrato(contratoId: number): void {
    this.router.navigate(['/contratos', contratoId]);
    this.searchControl.setValue('', { emitEvent: false });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
"""

SEARCH_BAR_HTML_CONTENT = r"""
<div class="search-container">
  <h3>Buscador de Contratos (Componente de Ejemplo)</h3>
  <input type="text" [formControl]="searchControl" placeholder="Buscar Administradora o Contrato...">
  <!-- Aquí iría el mat-autocomplete o una lista de resultados -->
</div>
"""

CONTRACT_DETAIL_TS_CONTENT = r"""
import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Subject, Observable } from 'rxjs';
import { switchMap, takeUntil, tap } from 'rxjs/operators';
// import { ApiService } from '../../core/services/api.service';
// import { Contrato } from '../../shared/models/contrato.model';

@Component({
  selector: 'app-contract-detail',
  templateUrl: './contract-detail.component.html',
  styleUrls: ['./contract-detail.component.scss']
})
export class ContractDetailComponent implements OnInit, OnDestroy {
  // contrato$: Observable<Contrato>;
  alertaCritica = false;
  private destroy$ = new Subject<void>();
  private audio: HTMLAudioElement;

  constructor(private route: ActivatedRoute) { // Inyectar ApiService
    this.audio = new Audio('assets/sounds/alert.mp3');
    this.audio.load();
  }

  ngOnInit(): void {
    // Simulación de datos para visualización
    this.route.paramMap.pipe(takeUntil(this.destroy$)).subscribe(params => {
        const id = Number(params.get('id'));
        console.log(`Cargando detalle para contrato ID: ${id}`);
        // this.contrato$ = this.apiService.getContratoDetalle(id).pipe(
        //   tap(contrato => this.checkAlertStatus(contrato))
        // );
        // Simulación:
        this.checkAlertStatus({ fecha_fin: '2026-08-01', alerta: { dias_previos: 90 } });
    });
  }

  checkAlertStatus(contrato: any): void {
    const fechaFin = new Date(contrato.fecha_fin);
    const hoy = new Date();
    const diffTime = fechaFin.getTime() - hoy.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= contrato.alerta.dias_previos) {
      this.alertaCritica = true;
      this.playAlertSound();
    }
  }

  async playAlertSound(): Promise<void> {
    try {
      await this.audio.play();
    } catch (err) {
      console.warn("Reproducción de audio bloqueada por el navegador.", err);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.audio) {
      this.audio.pause();
    }
  }
}
"""

CONTRACT_DETAIL_HTML_CONTENT = r"""
<!-- Banner de Alerta Crítica -->
<div *ngIf="alertaCritica" style="background-color: #D32F2F; color: white; padding: 1rem; text-align: center; font-weight: bold; animation: pulse 1.5s infinite;">
  ¡ALERTA! Este contrato está próximo a vencer.
</div>

<div style="padding: 2rem;">
  <h1>Detalle del Contrato (Componente de Ejemplo)</h1>
  <p>Aquí se mostrará la información detallada del contrato, el buscador de tarifas y los anexos.</p>
</div>
"""

# --- LÓGICA DEL SCRIPT ---

def create_file(path, content):
    """Crea un archivo en la ruta especificada con el contenido dado."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"   [OK] Archivo creado: {path}")

def run_command(command, cwd):
    """Ejecuta un comando de terminal en el directorio especificado."""
    print(f"\n> Ejecutando comando: '{' '.join(command)}' en '{cwd}'...")
    try:
        subprocess.run(command, cwd=cwd, check=True, shell=True)
        print(f"   [OK] Comando ejecutado exitosamente.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"   [ERROR] Falló la ejecución del comando: {e}")
        print(f"   Por favor, asegúrate de que el software necesario (como Angular CLI) esté instalado y en el PATH.")
        return False

def main():
    print("--- INICIANDO CONSTRUCCIÓN DEL PROYECTO 'clinica_centro_app' ---")
    
    # 1. Crear estructura base de Django
    print("\n[Paso 1/4] Creando estructura y archivos del Backend (Django)...")
    backend_path = "backend"
    project_name = "clinica_centro_api"
    app_name = "contratos"

    # Crear archivos específicos que definimos
    create_file(os.path.join(backend_path, app_name, "models.py"), MODELS_PY_CONTENT)
    create_file(os.path.join(backend_path, app_name, "services", "excel_processor.py"), EXCEL_PROCESSOR_PY_CONTENT)
    create_file(os.path.join(backend_path, app_name, "management", "commands", "check_contract_alerts.py"), CHECK_ALERTS_PY_CONTENT)
    create_file(os.path.join(backend_path, app_name, "serializers.py"), SERIALIZERS_PY_CONTENT)
    create_file(os.path.join(backend_path, app_name, "views.py"), VIEWS_PY_CONTENT)
    create_file(os.path.join(backend_path, app_name, "urls.py"), URLS_PY_CONTENT)
    
    # Crear archivos __init__.py para que Python reconozca los módulos
    create_file(os.path.join(backend_path, app_name, "services", "__init__.py"), "")
    create_file(os.path.join(backend_path, app_name, "management", "__init__.py"), "")
    create_file(os.path.join(backend_path, app_name, "management", "commands", "__init__.py"), "")

    # 2. Crear estructura base de Angular
    print("\n[Paso 2/4] Creando estructura y archivos del Frontend (Angular)...")
    frontend_path = "frontend"
    os.makedirs(frontend_path, exist_ok=True)
    
    if not run_command(["ng", "new", "frontend", "--directory=.", "--routing", "--style=scss", "--skip-install"], cwd=frontend_path):
        print("\n[ERROR CRÍTICO] No se pudo inicializar el proyecto de Angular. Abortando.")
        return

    # 3. Instalar PWA y crear componentes
    print("\n[Paso 3/4] Configurando PWA y generando componentes de Angular...")
    run_command(["ng", "add", "@angular/pwa", "--skip-confirmation"], cwd=frontend_path)
    run_command(["ng", "g", "c", "components/search-bar", "--skip-tests"], cwd=frontend_path)
    run_command(["ng", "g", "c", "components/contract-detail", "--skip-tests"], cwd=frontend_path)

    # Escribir el contenido de los componentes generados
    create_file(os.path.join(frontend_path, "src", "app", "components", "search-bar", "search-bar.component.ts"), SEARCH_BAR_TS_CONTENT)
    create_file(os.path.join(frontend_path, "src", "app", "components", "search-bar", "search-bar.component.html"), SEARCH_BAR_HTML_CONTENT)
    create_file(os.path.join(frontend_path, "src", "app", "components", "contract-detail", "contract-detail.component.ts"), CONTRACT_DETAIL_TS_CONTENT)
    create_file(os.path.join(frontend_path, "src", "app", "components", "contract-detail", "contract-detail.component.html"), CONTRACT_DETAIL_HTML_CONTENT)
    
    # Crear carpeta de sonidos
    os.makedirs(os.path.join(frontend_path, "src", "assets", "sounds"), exist_ok=True)
    print("   [OK] Carpeta 'frontend/src/assets/sounds' creada. (Recuerda añadir tu archivo alert.mp3 aquí)")

    # 4. Finalización y próximos pasos
    print("\n[Paso 4/4] ¡Estructura del proyecto creada exitosamente!")
    print("---")
    print("--- PRÓXIMOS PASOS (DEBES EJECUTARLOS MANUALMENTE) ---")
    print("\n--- CONFIGURACIÓN DEL BACKEND (DJANGO) ---")
    print("1. Navega a la carpeta del backend:")
    print("   cd backend")
    print("\n2. Crea el proyecto Django y la app (si el script no lo hizo):")
    print(f"   django-admin startproject {project_name} .")
    print(f"   python manage.py startapp {app_name}")
    print("   (Nota: El script ya creó los archivos de la app, solo necesitas la estructura base del proyecto)")
    print("\n3. Crea e inicia un entorno virtual:")
    print("   python -m venv venv")
    print(r"   .\venv\Scripts\activate")
    print("\n4. Instala las dependencias:")
    print("   pip install django djangorestframework pandas openpyxl django-cors-headers django-environ")
    print("\n5. Configura tu settings.py (añade 'contratos' y 'rest_framework' a INSTALLED_APPS).")
    print("\n6. Crea las migraciones y la base de datos:")
    print("   python manage.py makemigrations contratos")
    print("   python manage.py migrate")
    print("\n7. Inicia el servidor de desarrollo:")
    print("   python manage.py runserver")
    
    print("\n--- CONFIGURACIÓN DEL FRONTEND (ANGULAR) ---")
    print("1. Navega a la carpeta del frontend:")
    print("   cd frontend")
    print("\n2. Instala las dependencias de Node.js:")
    print("   npm install")
    print("\n3. (Opcional) Instala Angular Material:")
    print("   ng add @angular/material")
    print("\n4. Inicia el servidor de desarrollo de Angular:")
    print("   ng serve -o")

if __name__ == "__main__":
    main()

