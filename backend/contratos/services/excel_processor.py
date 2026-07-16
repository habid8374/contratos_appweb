
import unicodedata
import pandas as pd
from django.db import transaction
from contratos.models import DetalleTarifa, AnexoTarifario


def _norm(texto) -> str:
    """Normaliza un texto: minúsculas, sin tildes, sin espacios extra."""
    s = str(texto).strip().lower()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return ' '.join(s.split())


class ExcelTarifarioProcessor:
    """Procesa un Excel de tarifas reconociendo TODAS las hojas del libro, con
    tolerancia a que las columnas tengan nombres distintos entre archivos.

    Para cada hoja detecta, por palabras clave, las columnas de código,
    descripción, valor y tipo/manual de tarifa; y clasifica el tipo de
    tecnología según el nombre de la hoja.
    """

    # Palabras clave por campo, en orden de prioridad.
    KEYS_CODIGO = [
        'codigo cups', 'cod cups', 'cups', 'codigo propio', 'codigo ips',
        'codigo', 'cum', 'cod',
    ]
    KEYS_DESC = [
        'descripcion', 'servicio', 'medicamento', 'producto', 'nombre',
        'tecnologia', 'detalle',
    ]
    KEYS_VALOR = ['valor', 'tarifa', 'precio', 'costo']
    KEYS_MANUAL = ['tipo de tarifa', 'tipos de tarifa', 'manual', 'regulado', 'tipo']

    # (subcadena en el nombre de la hoja) -> tipo de tecnología
    TIPO_POR_HOJA = [
        ('medicamento', 'M'),
        ('farmac', 'M'),
        ('insumo', 'I'),
        ('material', 'I'),
        ('dispositivo', 'I'),
    ]

    def __init__(self, anexo_instance: AnexoTarifario, file_obj=None):
        if anexo_instance is None:
            raise ValueError("La instancia de AnexoTarifario no puede ser nula.")
        self.anexo = anexo_instance
        if file_obj is not None:
            self.source = file_obj
        elif anexo_instance.archivo_excel:
            self.source = anexo_instance.archivo_excel.path
        else:
            raise ValueError("No hay un archivo Excel para procesar.")

    def _tipo_por_hoja(self, nombre_hoja: str) -> str:
        n = _norm(nombre_hoja)
        for clave, tipo in self.TIPO_POR_HOJA:
            if clave in n:
                return tipo
        return 'P'

    @staticmethod
    def _pick_column(columnas_norm: dict, keys: list):
        """Devuelve el nombre original de la primera columna cuyo nombre
        normalizado contenga alguna de las palabras clave."""
        for key in keys:
            for original, norm in columnas_norm.items():
                if key in norm:
                    return original
        return None

    def process(self):
        if hasattr(self.source, 'seek'):
            self.source.seek(0)
        try:
            hojas = pd.read_excel(self.source, sheet_name=None)
        except Exception as e:
            raise IOError(f"No se pudo leer el archivo Excel: {e}")

        detalles = []
        resumen = {}

        for nombre_hoja, df in hojas.items():
            if df is None or df.empty:
                resumen[nombre_hoja] = 0
                continue

            df = df.dropna(how='all')
            columnas_norm = {c: _norm(c) for c in df.columns}
            col_codigo = self._pick_column(columnas_norm, self.KEYS_CODIGO)
            col_valor = self._pick_column(columnas_norm, self.KEYS_VALOR)
            col_desc = self._pick_column(columnas_norm, self.KEYS_DESC)
            col_manual = self._pick_column(columnas_norm, self.KEYS_MANUAL)

            # Se necesita al menos un código y un valor para poder cargar la hoja.
            if not col_codigo or not col_valor:
                resumen[nombre_hoja] = 'omitida (sin columna de código o valor)'
                continue

            tipo = self._tipo_por_hoja(nombre_hoja)
            count = 0
            for _, row in df.iterrows():
                codigo_raw = row.get(col_codigo)
                valor = pd.to_numeric(row.get(col_valor), errors='coerce')
                codigo = '' if pd.isna(codigo_raw) else str(codigo_raw).strip()
                # Los códigos numéricos llegan como 905702.0 -> 905702
                if codigo.endswith('.0'):
                    codigo = codigo[:-2]
                if not codigo or codigo.lower() == 'nan' or pd.isna(valor):
                    continue

                desc = ''
                if col_desc is not None:
                    d = row.get(col_desc)
                    desc = '' if pd.isna(d) else str(d).strip()
                manual = ''
                if col_manual is not None:
                    m = row.get(col_manual)
                    manual = '' if pd.isna(m) else str(m).strip()

                detalles.append(DetalleTarifa(
                    anexo_origen=self.anexo,
                    hoja=str(nombre_hoja)[:120],
                    codigo_cups=codigo[:60],
                    descripcion=desc[:500],
                    tipo_tecnologia=tipo,
                    esta_incluido=True,
                    manual_referencia=manual[:120],
                    tarifa_base=valor,
                    porcentaje_pactado=0,
                    valor_final=valor,
                ))
                count += 1
            resumen[nombre_hoja] = count

        if not detalles:
            raise ValueError(
                'No se encontraron filas con código y valor en ninguna hoja del archivo.'
            )

        with transaction.atomic():
            DetalleTarifa.objects.filter(anexo_origen=self.anexo).delete()
            DetalleTarifa.objects.bulk_create(detalles, batch_size=1000)

        return len(detalles), resumen
