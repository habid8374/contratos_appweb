import { Component, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import { ApiService, Contrato, ResultadoCarga } from '../../services/api.service';

@Component({
  selector: 'app-anexo-upload',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './anexo-upload.component.html',
  styleUrl: './anexo-upload.component.scss',
})
export class AnexoUploadComponent {
  private api = inject(ApiService);

  busqueda = new FormControl('', { nonNullable: true });
  resultados = signal<Contrato[]>([]);
  contrato = signal<Contrato | null>(null);

  nombreAnexo = new FormControl('', { nonNullable: true });
  archivo: File | null = null;

  cargando = signal(false);
  resultado = signal<ResultadoCarga | null>(null);
  error = signal<string | null>(null);

  constructor() {
    this.busqueda.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => this.api.buscarContratos(q || '')),
      )
      .subscribe((res) => this.resultados.set(res));
  }

  seleccionar(c: Contrato): void {
    this.contrato.set(c);
    this.resultados.set([]);
    this.busqueda.setValue(`${c.numero_contrato} — ${c.administradora?.nombre ?? ''}`, {
      emitEvent: false,
    });
  }

  onArchivo(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.archivo = input.files?.[0] ?? null;
  }

  subir(): void {
    const c = this.contrato();
    if (!c || !this.archivo) {
      this.error.set('Selecciona un contrato y un archivo Excel.');
      return;
    }
    this.cargando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.api
      .cargarAnexo(c.id, this.nombreAnexo.value || this.archivo.name, this.archivo)
      .subscribe({
        next: (r) => {
          this.cargando.set(false);
          this.resultado.set(r);
        },
        error: (err) => {
          this.cargando.set(false);
          this.error.set(err?.error?.error ?? 'No se pudo cargar el archivo.');
        },
      });
  }
}
