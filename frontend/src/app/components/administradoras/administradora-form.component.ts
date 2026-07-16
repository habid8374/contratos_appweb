import { Component, inject, signal, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-administradora-form',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="page-head">
      <h1>{{ id ? 'Editar' : 'Nueva' }} administradora</h1>
      <a routerLink="/administradoras" class="btn btn-outline">← Volver</a>
    </div>

    <form class="card" [formGroup]="form" (ngSubmit)="guardar()">
      <div class="form-grid">
        <label class="form-field full">
          <span>Nombre *</span>
          <input type="text" formControlName="nombre" />
        </label>
        <label class="form-field">
          <span>NIT *</span>
          <input type="text" formControlName="nit" />
        </label>
        <label class="form-field">
          <span>Régimen *</span>
          <select formControlName="regimen">
            <option value="SUB">Subsidiado</option>
            <option value="CON">Contributivo</option>
            <option value="AMB">Ambos</option>
            <option value="OTR">Otro</option>
          </select>
        </label>
        <label class="form-field">
          <span>Ciudad</span>
          <input type="text" formControlName="ciudad" />
        </label>
        <label class="form-field">
          <span>Departamento</span>
          <input type="text" formControlName="departamento" />
        </label>
        <label class="form-field">
          <span>Código postal</span>
          <input type="text" formControlName="codigo_postal" />
        </label>
        <label class="form-field">
          <span>Correo</span>
          <input type="email" formControlName="correo" />
        </label>
      </div>

      @if (error()) {
        <p class="msg-error">{{ error() }}</p>
      }

      <div class="form-actions">
        <button type="submit" class="btn btn-primary" [disabled]="guardando()">
          {{ guardando() ? 'Guardando…' : 'Guardar' }}
        </button>
        <a routerLink="/administradoras" class="btn btn-outline">Cancelar</a>
      </div>
    </form>
  `,
})
export class AdministradoraFormComponent implements OnInit {
  private fb = inject(FormBuilder);
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  id: number | null = null;
  guardando = signal(false);
  error = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    nombre: ['', Validators.required],
    nit: ['', Validators.required],
    regimen: ['OTR', Validators.required],
    ciudad: [''],
    departamento: [''],
    codigo_postal: [''],
    correo: [''],
  });

  ngOnInit(): void {
    const param = this.route.snapshot.paramMap.get('id');
    if (param) {
      this.id = Number(param);
      this.api.getAdministradora(this.id).subscribe((a) => this.form.patchValue(a));
    }
  }

  guardar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.guardando.set(true);
    this.error.set(null);
    const data = this.form.getRawValue();
    const req = this.id
      ? this.api.actualizarAdministradora(this.id, data)
      : this.api.crearAdministradora(data);

    req.subscribe({
      next: () => this.router.navigate(['/administradoras']),
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
    return 'No se pudo guardar. Revisa los datos.';
  }
}
