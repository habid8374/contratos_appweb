
import re
from datetime import datetime, date as _date

import pandas as pd
from django.db import transaction

from contratos.models import NotaTecnica, LineaNotaTecnica, RegistroConsumo
from contratos.services.excel_processor import _norm


def _parse_fecha(val, defecto=None):
    if pd.isna(val):
        return defecto
    if isinstance(val, pd.Timestamp) or isinstance(val, datetime):
        return val.date()
    if isinstance(val, _date):
        return val
    s = str(val).strip()
    if not s:
        return defecto
    try:
        # Fechas ISO (YYYY-MM-DD) sin dayfirst; el resto en formato colombiano.
        if re.match(r'^\d{4}-\d{1,2}-\d{1,2}', s):
            return pd.to_datetime(s).date()
        return pd.to_datetime(s, dayfirst=True).date()
    except Exception:
        return defecto


def _pick(columnas_norm: dict, keys: list):
    for key in keys:
        for original, norm in columnas_norm.items():
            if key in norm:
                return original
    return None


def _num(valor, defecto=0.0):
    v = pd.to_numeric(valor, errors='coerce')
    return defecto if pd.isna(v) else float(v)


def _texto(row, col):
    if not col:
        return ''
    v = row.get(col)
    return '' if pd.isna(v) else str(v).strip()


def _codigo(row, col):
    cod = _texto(row, col)
    if cod.endswith('.0'):
        cod = cod[:-2]
    return cod


def procesar_nota_tecnica(nota: NotaTecnica, file_obj) -> int:
    """Carga las líneas presupuestadas de una nota técnica desde un Excel."""
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
    hojas = pd.read_excel(file_obj, sheet_name=None)

    lineas = []
    for _, df in hojas.items():
        if df is None or df.empty:
            continue
        df = df.dropna(how='all')
        cols = {c: _norm(c) for c in df.columns}
        col_cod = _pick(cols, ['codigo cups', 'cups', 'codigo', 'cod', 'actividad'])
        col_desc = _pick(cols, ['descripcion', 'servicio', 'actividad', 'nombre', 'detalle'])
        col_freq = _pick(cols, ['frecuencia', 'eventos', 'casos', 'cantidad', 'numero', 'freq'])
        col_unit = _pick(cols, ['valor unitario', 'vr unitario', 'valor unit', 'unitario',
                                'costo unitario', 'tarifa'])
        col_total = _pick(cols, ['valor total', 'vr total', 'valor presupuestado', 'presupuesto',
                                 'valor mes', 'valor anual', 'total'])
        col_valor = _pick(cols, ['valor', 'costo'])
        # Evitar que 'total'/'valor' apunten a la misma columna del unitario.
        if col_total == col_unit:
            col_total = None
        if col_valor == col_unit:
            col_valor = None
        if not col_cod:
            continue
        for _, row in df.iterrows():
            cod = _codigo(row, col_cod)
            if not cod or cod.lower() == 'nan':
                continue
            freq = _num(row.get(col_freq)) if col_freq else 0.0
            unit = _num(row.get(col_unit)) if col_unit else 0.0
            total = _num(row.get(col_total)) if col_total else 0.0
            if not total:
                if unit and freq:
                    total = unit * freq
                elif col_valor:
                    total = _num(row.get(col_valor))
            if not unit and freq and total:
                unit = total / freq
            lineas.append(LineaNotaTecnica(
                nota_tecnica=nota,
                codigo=cod[:60],
                descripcion=_texto(row, col_desc)[:500],
                frecuencia_esperada=freq,
                valor_unitario=unit,
                valor_total=total,
            ))

    if not lineas:
        raise ValueError('No se encontraron actividades con código en el archivo.')

    with transaction.atomic():
        LineaNotaTecnica.objects.filter(nota_tecnica=nota).delete()
        LineaNotaTecnica.objects.bulk_create(lineas, batch_size=1000)
        if not nota.valor_global:
            nota.valor_global = sum((l.valor_total for l in lineas), 0)
            nota.save(update_fields=['valor_global'])

    return len(lineas)


def procesar_consumo(contrato, file_obj, fecha_defecto=None) -> int:
    """Carga registros de consumo (ejecución) desde un Excel. Si una fila no
    trae fecha, usa `fecha_defecto` (p. ej. el primer día del mes en curso)."""
    if hasattr(file_obj, 'seek'):
        file_obj.seek(0)
    hojas = pd.read_excel(file_obj, sheet_name=None)

    registros = []
    for _, df in hojas.items():
        if df is None or df.empty:
            continue
        df = df.dropna(how='all')
        cols = {c: _norm(c) for c in df.columns}
        col_fecha = _pick(cols, ['fecha', 'dia', 'atencion', 'prestacion'])
        col_cod = _pick(cols, ['codigo cups', 'cups', 'codigo', 'cod'])
        col_desc = _pick(cols, ['descripcion', 'servicio', 'nombre'])
        col_cant = _pick(cols, ['cantidad', 'cant', 'eventos', 'numero'])
        col_valor = _pick(cols, ['valor total', 'vr total', 'total', 'valor', 'costo'])
        if not col_valor and not col_cant:
            continue
        for _, row in df.iterrows():
            fecha = _parse_fecha(row.get(col_fecha), fecha_defecto) if col_fecha else fecha_defecto
            if fecha is None:
                continue
            valor = _num(row.get(col_valor)) if col_valor else 0.0
            cant = _num(row.get(col_cant), defecto=1.0) if col_cant else 1.0
            if valor == 0 and cant == 0:
                continue
            registros.append(RegistroConsumo(
                contrato=contrato,
                fecha=fecha,
                codigo=_codigo(row, col_cod)[:60],
                descripcion=_texto(row, col_desc)[:500],
                cantidad=cant,
                valor_total=valor,
            ))

    if not registros:
        raise ValueError('No se encontraron registros de consumo válidos en el archivo.')

    RegistroConsumo.objects.bulk_create(registros, batch_size=1000)
    return len(registros)
