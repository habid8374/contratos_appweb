import { Component, inject, signal, OnInit } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService, Administradora, Contrato } from '../../services/api.service';

@Component({
  selector: 'app-administradora-detalle',
  standalone: true,
  imports: [RouterLink],
  template: `
    @if (administradora(); as a) {
      <div class="page-head">
        <h1>{{ a.nombre }}</h1>
        <div class="acciones">
          <a routerLink="/administradoras" class="btn btn-outline">← Volver</a>
          <a [routerLink]="['/administradoras', a.id, 'editar']" class="btn btn-outline">Editar</a>
          <a [routerLink]="['/contratos/nuevo']" [queryParams]="{ administradora: a.id }" class="btn btn-primary">
            + Nuevo contrato
          </a>
        </div>
      </div>

      <div class="card datos">
        <div><span>NIT</span><strong>{{ a.nit }}</strong></div>
        <div><span>Régimen</span><strong>{{ a.regimen_display }}</strong></div>
        <div><span>Ciudad</span><strong>{{ a.ciudad || '—' }}</strong></div>
        <div><span>Departamento</span><strong>{{ a.departamento || '—' }}</strong></div>
        <div><span>Código postal</span><strong>{{ a.codigo_postal || '—' }}</strong></div>
        <div><span>Correo</span><strong>{{ a.correo || '—' }}</strong></div>
      </div>

      <h2 class="sub">Contratos</h2>
      @if (contratos().length) {
        <div class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th>N° contrato</th>
                <th>Modalidad</th>
                <th>Vigencia</th>
                <th>Estado</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              @for (c of contratos(); track c.id) {
                <tr>
                  <td>{{ c.numero_contrato }}</td>
                  <td>{{ c.modalidad }}</td>
                  <td>{{ c.fecha_inicio }} → {{ c.fecha_fin }}</td>
                  <td>
                    <span class="chip" [class.chip-ok]="c.estado === 'ACT'" [class.chip-no]="c.estado !== 'ACT'">
                      {{ c.estado === 'ACT' ? 'Activo' : 'Inactivo' }}
                    </span>
                  </td>
                  <td class="acciones">
                    <a [routerLink]="['/contratos', c.id]" class="btn btn-outline btn-sm">Ver</a>
                    <a [routerLink]="['/contratos', c.id, 'editar']" class="btn btn-outline btn-sm">Editar</a>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p class="vacio">Esta administradora aún no tiene contratos.</p>
      }
    }
  `,
  styles: [`
    .acciones { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .datos {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 0.9rem;
      margin-bottom: 1.5rem;
    }
    .datos div { display: flex; flex-direction: column; gap: 0.15rem; }
    .datos span { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }
    .datos strong { color: var(--navy); }
    .sub { color: var(--navy); font-size: 1.15rem; margin: 0 0 0.8rem; }
    .vacio { color: var(--muted); }
    td.acciones { display: flex; gap: 0.4rem; }
  `],
})
export class AdministradoraDetalleComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);

  administradora = signal<Administradora | null>(null);
  contratos = signal<Contrato[]>([]);

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.getAdministradora(id).subscribe((a) => this.administradora.set(a));
    this.api.getContratos(id).subscribe((c) => this.contratos.set(c));
  }
}
