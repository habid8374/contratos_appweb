import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Administradora {
  id?: number;
  nombre: string;
  nit: string;
  regimen: string;
  regimen_display?: string;
  ciudad?: string;
  departamento?: string;
  codigo_postal?: string;
  correo?: string;
  total_contratos?: number;
}

export interface Alerta {
  dias_previos: number;
  activa: boolean;
  ultima_notificacion_enviada?: string | null;
}

export interface Contrato {
  id: number;
  numero_contrato: string;
  administradora?: Administradora;
  modalidad: string;
  objeto?: string;
  fecha_inicio?: string;
  fecha_fin?: string;
  valor_total?: string;
  manual_referencia?: string;
  porcentaje_negociado?: string;
  estado: string;
  regimen_estimado?: string;
  documento_negociacion?: string | null;
  alerta?: Alerta | null;
  dias_para_vencer?: number | null;
  total_tarifas?: number;
}

export interface Tarifa {
  id: number;
  hoja: string;
  codigo_cups: string;
  descripcion: string;
  tipo_tecnologia: string;
  tipo_tecnologia_display: string;
  esta_incluido: boolean;
  manual_referencia: string;
  tarifa_base: string;
  porcentaje_pactado: string;
  valor_final: string;
}

export interface ResultadoCarga {
  id: number;
  nombre_anexo: string;
  filas_procesadas: number;
  resumen_hojas: Record<string, number | string>;
}

export interface AlertaResumen {
  id: number;
  numero_contrato: string;
  administradora: string;
  fecha_inicio: string;
  fecha_fin: string;
  dias_para_vencer: number | null;
  dias_previos: number | null;
  alerta_activa: boolean;
  en_alerta: boolean;
  vencido: boolean;
}

export interface NotaTecnica {
  id: number;
  contrato: number;
  anio: number;
  mes: number;
  poblacion: number;
  valor_global: string;
  total_lineas?: number;
}

export interface ActividadPgp {
  codigo: string;
  descripcion: string;
  frecuencia_esperada: number;
  valor_presupuestado: number;
  cantidad_ejecutada: number;
  valor_ejecutado: number;
}

export interface TableroPgp {
  anio: number;
  mes: number;
  tiene_nota: boolean;
  poblacion: number;
  techo: number;
  total_ejecutado: number;
  saldo: number | null;
  porcentaje_ejecucion: number | null;
  total_registros: number;
  actividades: ActividadPgp[];
  serie_diaria: { fecha: string; valor: number }[];
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly baseUrl = `${environment.apiUrl}/api`;
  private http = inject(HttpClient);

  // ---- Administradoras ----
  getAdministradoras(q = ''): Observable<Administradora[]> {
    return this.http.get<Administradora[]>(`${this.baseUrl}/administradoras/`, { params: { q } });
  }
  getAdministradora(id: number): Observable<Administradora> {
    return this.http.get<Administradora>(`${this.baseUrl}/administradoras/${id}/`);
  }
  crearAdministradora(data: Administradora): Observable<Administradora> {
    return this.http.post<Administradora>(`${this.baseUrl}/administradoras/`, data);
  }
  actualizarAdministradora(id: number, data: Administradora): Observable<Administradora> {
    return this.http.put<Administradora>(`${this.baseUrl}/administradoras/${id}/`, data);
  }
  eliminarAdministradora(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/administradoras/${id}/`);
  }

  // ---- Contratos ----
  getContratos(administradoraId?: number): Observable<Contrato[]> {
    const params: Record<string, string> = {};
    if (administradoraId) {
      params['administradora'] = String(administradoraId);
    }
    return this.http.get<Contrato[]>(`${this.baseUrl}/contratos/`, { params });
  }
  buscarContratos(query: string): Observable<Contrato[]> {
    return this.http.get<Contrato[]>(`${this.baseUrl}/contratos/buscar/`, { params: { q: query } });
  }
  getAlertas(): Observable<AlertaResumen[]> {
    return this.http.get<AlertaResumen[]>(`${this.baseUrl}/contratos/alertas/`);
  }
  getContratoDetalle(id: number): Observable<Contrato> {
    return this.http.get<Contrato>(`${this.baseUrl}/contratos/${id}/`);
  }
  crearContrato(data: Partial<Contrato>): Observable<Contrato> {
    return this.http.post<Contrato>(`${this.baseUrl}/contratos/`, data);
  }
  actualizarContrato(id: number, data: Partial<Contrato>): Observable<Contrato> {
    return this.http.patch<Contrato>(`${this.baseUrl}/contratos/${id}/`, data);
  }
  eliminarContrato(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/contratos/${id}/`);
  }
  subirPdfContrato(id: number, archivo: File): Observable<Contrato> {
    const form = new FormData();
    form.append('documento_negociacion', archivo);
    return this.http.patch<Contrato>(`${this.baseUrl}/contratos/${id}/`, form);
  }

  // ---- Tarifas / anexos ----
  getTarifas(id: number, query = ''): Observable<Tarifa[]> {
    return this.http.get<Tarifa[]>(`${this.baseUrl}/contratos/${id}/tarifas/`, {
      params: { q: query },
    });
  }
  cargarAnexo(contratoId: number, nombreAnexo: string, archivo: File): Observable<ResultadoCarga> {
    const form = new FormData();
    form.append('contrato', String(contratoId));
    form.append('nombre_anexo', nombreAnexo);
    form.append('archivo_excel', archivo);
    return this.http.post<ResultadoCarga>(`${this.baseUrl}/anexos/`, form);
  }

  // ---- PGP ----
  getTableroPgp(contratoId: number, anio: number, mes: number): Observable<TableroPgp> {
    return this.http.get<TableroPgp>(`${this.baseUrl}/contratos/${contratoId}/pgp/`, {
      params: { anio: String(anio), mes: String(mes) },
    });
  }
  getNotaTecnica(contratoId: number, anio: number, mes: number): Observable<NotaTecnica[]> {
    return this.http.get<NotaTecnica[]>(`${this.baseUrl}/notas-tecnicas/`, {
      params: { contrato: String(contratoId), anio: String(anio), mes: String(mes) },
    });
  }
  crearNotaTecnica(contratoId: number, anio: number, mes: number, poblacion: number): Observable<NotaTecnica> {
    return this.http.post<NotaTecnica>(`${this.baseUrl}/notas-tecnicas/`, {
      contrato: contratoId, anio, mes, poblacion,
    });
  }
  cargarNotaTecnica(notaId: number, archivo: File): Observable<NotaTecnica & { lineas_procesadas: number }> {
    const form = new FormData();
    form.append('archivo_excel', archivo);
    return this.http.post<NotaTecnica & { lineas_procesadas: number }>(
      `${this.baseUrl}/notas-tecnicas/${notaId}/cargar/`, form,
    );
  }
  cargarConsumo(contratoId: number, anio: number, mes: number, archivo: File): Observable<{ registros_procesados: number }> {
    const form = new FormData();
    form.append('contrato', String(contratoId));
    form.append('anio', String(anio));
    form.append('mes', String(mes));
    form.append('archivo_excel', archivo);
    return this.http.post<{ registros_procesados: number }>(`${this.baseUrl}/consumo/`, form);
  }
}
