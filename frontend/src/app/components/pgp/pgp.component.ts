import { Component, inject, signal, computed } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { ApiService, Contrato, TableroPgp } from '../../services/api.service';

@Component({
  selector: 'app-pgp',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './pgp.component.html',
  styleUrl: './pgp.component.scss',
})
export class PgpComponent {
  private api = inject(ApiService);

  meses = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ];

  busqueda = new FormControl('', { nonNullable: true });
  resultados = signal<Contrato[]>([]);
  contrato = signal<Contrato | null>(null);

  anio = signal(new Date().getFullYear());
  mes = signal(new Date().getMonth() + 1);

  tablero = signal<TableroPgp | null>(null);
  cargando = signal(false);
  mensaje = signal<string | null>(null);
  error = signal<string | null>(null);

  maxSerie = computed(() => {
    const s = this.tablero()?.serie_diaria ?? [];
    return s.reduce((m, x) => Math.max(m, x.valor), 0) || 1;
  });

  anios = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i);

  constructor() {
    this.busqueda.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => this.api.buscarContratos(q || '')),
      )
      .subscribe((r) => this.resultados.set(r));
  }

  seleccionar(c: Contrato): void {
    this.contrato.set(c);
    this.resultados.set([]);
    this.busqueda.setValue(`${c.numero_contrato} — ${c.administradora?.nombre ?? ''}`, {
      emitEvent: false,
    });
    this.cargarTablero();
  }

  cambiarPeriodo(): void {
    if (this.contrato()) {
      this.cargarTablero();
    }
  }

  cargarTablero(): void {
    const c = this.contrato();
    if (!c) return;
    this.cargando.set(true);
    this.error.set(null);
    this.mensaje.set(null);
    this.api.getTableroPgp(c.id, this.anio(), this.mes()).subscribe({
      next: (t) => {
        this.tablero.set(t);
        this.cargando.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar el tablero.');
        this.cargando.set(false);
      },
    });
  }

  onNotaFile(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.subirNota(file);
  }

  private subirNota(file: File): void {
    const c = this.contrato();
    if (!c) return;
    this.cargando.set(true);
    this.error.set(null);
    // Buscar la nota técnica del periodo; si no existe, crearla, y luego cargar.
    this.api.getNotaTecnica(c.id, this.anio(), this.mes()).subscribe((notas) => {
      const notaId$ = notas.length
        ? Promise.resolve(notas[0].id)
        : new Promise<number>((resolve, reject) =>
            this.api
              .crearNotaTecnica(c.id, this.anio(), this.mes(), 0)
              .subscribe({ next: (n) => resolve(n.id), error: reject }),
          );
      notaId$.then((id) => {
        this.api.cargarNotaTecnica(id, file).subscribe({
          next: (r) => {
            this.mensaje.set(`Nota técnica cargada: ${r.lineas_procesadas} actividades.`);
            this.cargarTablero();
          },
          error: (err) => {
            this.error.set(err?.error?.error ?? 'No se pudo cargar la nota técnica.');
            this.cargando.set(false);
          },
        });
      }).catch(() => {
        this.error.set('No se pudo crear la nota técnica.');
        this.cargando.set(false);
      });
    });
  }

  onConsumoFile(event: Event): void {
    const file = (event.target as HTMLInputElement).files?.[0];
    if (file) this.subirConsumo(file);
  }

  private subirConsumo(file: File): void {
    const c = this.contrato();
    if (!c) return;
    this.cargando.set(true);
    this.error.set(null);
    this.api.cargarConsumo(c.id, this.anio(), this.mes(), file).subscribe({
      next: (r) => {
        this.mensaje.set(`Consumo cargado: ${r.registros_procesados} registros.`);
        this.cargarTablero();
      },
      error: (err) => {
        this.error.set(err?.error?.error ?? 'No se pudo cargar el consumo.');
        this.cargando.set(false);
      },
    });
  }

  pct(a: { valor_ejecutado: number; valor_presupuestado: number }): number | null {
    return a.valor_presupuestado ? Math.round((a.valor_ejecutado / a.valor_presupuestado) * 100) : null;
  }

  fmt(v: number | string | null): string {
    if (v === null || v === undefined) return '—';
    return Number(v).toLocaleString('es-CO');
  }
}
