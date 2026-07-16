import { Injectable, inject, signal, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';

export interface Usuario {
  id: number;
  username: string;
  nombre: string;
  email: string;
  is_staff: boolean;
}

interface TokenPair {
  access: string;
  refresh: string;
}

const ACCESS_KEY = 'appweb_access';
const REFRESH_KEY = 'appweb_refresh';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private readonly isBrowser = isPlatformBrowser(this.platformId);

  readonly usuario = signal<Usuario | null>(null);

  login(username: string, password: string): Observable<TokenPair> {
    return this.http
      .post<TokenPair>('/api/auth/token/', { username, password })
      .pipe(tap((tokens) => this.guardarTokens(tokens)));
  }

  cargarUsuario(): Observable<Usuario> {
    return this.http
      .get<Usuario>('/api/auth/me/')
      .pipe(tap((u) => this.usuario.set(u)));
  }

  refrescar(): Observable<{ access: string }> {
    const refresh = this.getRefresh();
    return this.http
      .post<{ access: string }>('/api/auth/token/refresh/', { refresh })
      .pipe(tap(({ access }) => this.setItem(ACCESS_KEY, access)));
  }

  logout(): void {
    this.usuario.set(null);
    if (this.isBrowser) {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    }
  }

  isAuthenticated(): boolean {
    return !!this.getAccess();
  }

  getAccess(): string | null {
    return this.getItem(ACCESS_KEY);
  }

  getRefresh(): string | null {
    return this.getItem(REFRESH_KEY);
  }

  private guardarTokens(tokens: TokenPair): void {
    this.setItem(ACCESS_KEY, tokens.access);
    this.setItem(REFRESH_KEY, tokens.refresh);
  }

  private getItem(key: string): string | null {
    return this.isBrowser ? localStorage.getItem(key) : null;
  }

  private setItem(key: string, value: string): void {
    if (this.isBrowser) {
      localStorage.setItem(key, value);
    }
  }
}
