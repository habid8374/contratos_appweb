import { Component, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService, Administradora, Contrato } from '../../services/api.service';

@Component({
  selector: 'app-contrato-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="page-head">
      <h1>{{ id ? 'Editar' : 'Nuevo' }} contrato</h1>
      <a routerLink="/administradoras" class="btn btn-outline">← Administradoras</a>
    </div>

    <form class="card" [formGroup]="form" (ngSubmit)="guardar()">
      <div class="form-grid">
        <label class="form-field">
          <span>Administradora *</span>
          <select formControlName="administradora">
            <option [ngValue]="null" disabled>Selecciona…</option>
            @for (a of administradoras(); track a.id) {
              <option [ngValue]="a.id">{{ a.nombre }} ({{ a.regimen_display }})</option>
            }
          </select>
        </label>
        <label class="form-field">
          <span>N° de contrato *</span>
          <input type="text" formControlName="numero_contrato" />
        </label>
        <label class="form-field">
          <span>Modalidad *</span>
          <select formControlName="modalidad">
            <option value="EV">Evento</option>
            <option value="CAP">Capitación</option>
            <option value="PGP">PGP</option>
          </select>
        </label>
        <label class="form-field">
          <span>Estado *</span>
          <select formControlName="estado">
            <option value="ACT">Activo</option>
            <option value="INA">Inactivo</option>
          </select>
        </label>
        <label class="form-field">
          <span>Fecha inicio *</span>
          <input type="date" formControlName="fecha_inicio" />
        </label>
        <label class="form-field">
          <span>Fecha fin *</span>
          <input type="date" formControlName="fecha_fin" />
        </label>
        <label class="form-field">
          <span>Valor total</span>
          <input type="number" formControlName="valor_total" step="0.01" />
        </label>
        <label class="form-field">
          <span>Manual de referencia</span>
          <input type="text" formControlName="manual_referencia" placeholder="Ej: ISS 2001, SOAT, Propio" />
        </label>
        <label class="form-field">
          <span>Porcentaje pactado (%)</span>
          <input type="number" formControlName="porcentaje_negociado" step="0.01" placeholder="Ej: 35" />
        </label>
        <label class="form-field full">
          <span>Objeto</span>
          <textarea rows="3" formControlName="objeto"></textarea>
        </label>
      </div>

      <fieldset class="alerta" formGroupName="alerta">
        <legend>Alerta de vencimiento</legend>
        <div class="alerta-row">
          <label class="form-field">
            <span>Avisar días antes de vencer</span>
            <input type="number" formControlName="dias_previos" min="1" />
          </label>
          <label class="check">
            <input type="checkbox" formControlName="activa" />
            <span>Alerta activa</span>
          </label>
        </div>
      </fieldset>

      <label class="form-field pdf">
        <span>Documento de negociación (PDF)</span>
        @if (pdfActual()) {
          <a [href]="pdfActual()" target="_blank" class="pdf-link">Ver PDF actual</a>
        }
        <input type="file" accept="application/pdf" (change)="onPdf($event)" />
      </label>

      @if (error()) {
        <p class="msg-error">{{ error() }}</p>
      }

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" [disabled]="guardando()">
          {{ guardando() ? 'Guardando…' : 'Guardar contrato' }}
        </button>
        <a routerLink="/administradoras" class="btn btn-outline">Cancelar</a>
      </div>
    </form>
  `,
  styles: [`
    .alerta {
      border: 1px solid var(--border);
      border-radius: 11px;
      padding: 1rem 1.2rem;
      margin-top: 1.25rem;
    }
    .alerta legend { color: var(--navy); font-weight: 600; padding: 0 0.4rem; }
    .alerta-row { display: flex; align-items: flex-end; gap: 1.5rem; flex-wrap: wrap; }
    .check { display: flex; align-items: center; gap: 0.4rem; font-size: 0.9rem; }
    .pdf { margin-top: 1.25rem; max-width: 460px; }
    .pdf-link { color: var(--teal); font-size: 0.85rem; }
  `],
})
export class ContratoFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  id: number | null = null;
  administradoras = signal<Administradora[]>([]);
  pdfActual = signal<string | null>(null);
  guardando = signal(false);
  error = signal<string | null>(null);
  private pdf: File | null = null;

  form = this.fb.group({
    numero_contrato: ['', Validators.required],
    administradora: this.fb.control<number | null>(null, Validators.required),
    modalidad: ['EV', Validators.required],
    estado: ['ACT', Validators.required],
    fecha_inicio: ['', Validators.required],
    fecha_fin: ['', Validators.required],
    valor_total: this.fb.control<number | null>(null),
    manual_referencia: [''],
    porcentaje_negociado: this.fb.control<number | null>(0),
    objeto: [''],
    alerta: this.fb.group({
      dias_previos: [90, Validators.required],
      activa: [true],
    }),
  });

  ngOnInit(): void {
    this.api.getAdministradoras().subscribe((a) => this.administradoras.set(a));

    const param = this.route.snapshot.paramMap.get('id');
    const adminQuery = this.route.snapshot.queryParamMap.get('administradora');

    if (param) {
      this.id = Number(param);
      this.api.getContratoDetalle(this.id).subscribe((c) => {
        this.form.patchValue({
          numero_contrato: c.numero_contrato,
          administradora: c.administradora?.id ?? null,
          modalidad: c.modalidad,
          estado: c.estado,
          fecha_inicio: c.fecha_inicio ?? '',
          fecha_fin: c.fecha_fin ?? '',
          valor_total: c.valor_total ? Number(c.valor_total) : null,
          manual_referencia: c.manual_referencia ?? '',
          porcentaje_negociado: c.porcentaje_negociado ? Number(c.porcentaje_negociado) : 0,
          objeto: c.objeto ?? '',
          alerta: {
            dias_previos: c.alerta?.dias_previos ?? 90,
            activa: c.alerta?.activa ?? true,
          },
        });
        this.pdfActual.set(c.documento_negociacion ?? null);
      });
    } else if (adminQuery) {
      this.form.patchValue({ administradora: Number(adminQuery) });
    }
  }

  onPdf(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.pdf = input.files?.[0] ?? null;
  }

  guardar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Completa los campos obligatorios (*).');
      return;
    }
    this.guardando.set(true);
    this.error.set(null);
    const data = this.form.getRawValue() as unknown as Partial<Contrato>;

    const req = this.id
      ? this.api.actualizarContrato(this.id, data)
      : this.api.crearContrato(data);

    req.subscribe({
      next: (contrato) => {
        if (this.pdf) {
          this.api.subirPdfContrato(contrato.id, this.pdf).subscribe({
            next: () => this.router.navigate(['/contratos', contrato.id]),
            error: () => {
              this.guardando.set(false);
              this.error.set('El contrato se guardó, pero el PDF no se pudo subir.');
            },
          });
        } else {
          this.router.navigate(['/contratos', contrato.id]);
        }
      },
      error: (err) => {
        this.guardando.set(false);
        this.error.set(this.formatError(err));
      },
    });
  }

  private formatError(err: any): string {
    if (err?.error && typeof err.error === 'object') {
      const campos = Object.entries(err.error)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') : v}`)
        .join(' · ');
      if (campos) {
        return campos;
      }
    }
    return 'No se pudo guardar el contrato.';
  }
}
