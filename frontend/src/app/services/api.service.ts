import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface Administradora {
  nombre: string;
  nit: string;
  regimen?: string;
  regimen_display?: string;
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
  estado: string;
  regimen_estimado?: string;
}

export interface Tarifa {
  id: number;
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
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly baseUrl = `${environment.apiUrl}/api`;
  private http = inject(HttpClient);

  buscarContratos(query: string): Observable<Contrato[]> {
    return this.http.get<Contrato[]>(`${this.baseUrl}/contratos/buscar/`, {
      params: { q: query },
    });
  }

  getContratoDetalle(id: number): Observable<Contrato> {
    return this.http.get<Contrato>(`${this.baseUrl}/contratos/${id}/`);
  }

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
}
