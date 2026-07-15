import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Administradora {
  nombre: string;
  nit: string;
}

export interface Contrato {
  id: number;
  numero_contrato: string;
  administradora?: Administradora;
  modalidad: string;
  fecha_fin?: string;
  estado: string;
  objeto?: string;
}

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private readonly baseUrl = '/api';

  constructor(private http: HttpClient) {}

  buscarContratos(query: string): Observable<Contrato[]> {
    return this.http.get<Contrato[]>(`${this.baseUrl}/contratos/buscar/`, {
      params: { q: query },
    });
  }

  getContratoDetalle(id: number): Observable<Contrato> {
    return this.http.get<Contrato>(`${this.baseUrl}/contratos/${id}/`);
  }
}
