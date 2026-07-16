import { Component, inject, signal, OnInit } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { ApiService, Administradora } from '../../services/api.service';

@Component({
  selector: 'app-administradoras-list',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="page-head">
      <h1>Administradoras / EPS</h1>
      <a routerLink="/administradoras/nueva" class="btn btn-primary">+ Nueva administradora</a>
    </div>

    <input
      class="buscador"
      type="text"
      [formControl]="busqueda"
      placeholder="Buscar por nombre o NIT…"
      autocomplete="off"
    />

    @if (administradoras().length) {
      <div class="tabla-wrap">
        <table class="tabla">
          <thead>
            <tr>
              <th>Nombre</th>
              <th>NIT</th>
              <th>Régimen</th>
              <th>Ciudad</th>
              <th>Contratos</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (a of administradoras(); track a.id) {
              <tr>
                <td>{{ a.nombre }}</td>
                <td>{{ a.nit }}</td>
                <td><span class="chip chip-teal">{{ a.regimen_display }}</span></td>
                <td>{{ a.ciudad || '—' }}</td>
                <td>{{ a.total_contratos }}</td>
                <td class="acciones">
                  <a [routerLink]="['/administradoras', a.id]" class="btn btn-outline btn-sm">Contratos</a>
                  <a [routerLink]="['/administradoras', a.id, 'editar']" class="btn btn-outline btn-sm">Editar</a>
                  <button class="btn btn-danger btn-sm" (click)="eliminar(a)">Eliminar</button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    } @else {
      <p class="vacio">No hay administradoras todavía. Crea la primera con el botón de arriba.</p>
    }

    @if (error()) {
      <p class="msg-error">{{ error() }}</p>
    }
  `,
  styles: [`
    .buscador {
      width: 100%;
      padding: 0.7rem 0.9rem;
      border: 1px solid #d1d5db;
      border-radius: 11px;
      font-size: 0.95rem;
      margin-bottom: 1rem;
    }
    .buscador:focus {
      outline: none;
      border-color: var(--teal);
      box-shadow: 0 0 0 3px rgba(30, 139, 156, 0.15);
    }
    .acciones {
      display: flex;
      gap: 0.4rem;
      justify-content: flex-end;
    }
    .vacio {
      color: var(--muted);
    }
  `],
})
export class AdministradorasListComponent implements OnInit {
  private api = inject(ApiService);

  administradoras = signal<Administradora[]>([]);
  busqueda = new FormControl('', { nonNullable: true });
  error = signal<string | null>(null);

  ngOnInit(): void {
    this.cargar('');
    this.busqueda.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => this.api.getAdministradoras(q || '')),
      )
      .subscribe((res) => this.administradoras.set(res));
  }

  private cargar(q: string): void {
    this.api.getAdministradoras(q).subscribe({
      next: (res) => this.administradoras.set(res),
      error: () => this.error.set('No se pudieron cargar las administradoras.'),
    });
  }

  eliminar(a: Administradora): void {
    if (!a.id || !confirm(`¿Eliminar la administradora "${a.nombre}"?`)) {
      return;
    }
    this.error.set(null);
    this.api.eliminarAdministradora(a.id).subscribe({
      next: () => this.cargar(this.busqueda.value),
      error: (err) =>
        this.error.set(err?.error?.error ?? 'No se pudo eliminar la administradora.'),
    });
  }
}
