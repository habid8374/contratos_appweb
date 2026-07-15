
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
