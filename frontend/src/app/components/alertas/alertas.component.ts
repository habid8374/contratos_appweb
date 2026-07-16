import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService, AlertaResumen } from '../../services/api.service';

@Component({
  selector: 'app-alertas',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="page-head">
      <h1>Alertas de vencimiento</h1>
      <a routerLink="/" class="btn btn-outline">← Inicio</a>
    </div>

    <div class="resumen">
      <div class="tile tile-danger">
        <span class="num">{{ vencidos().length }}</span>
        <span class="lbl">Vencidos</span>
      </div>
      <div class="tile tile-warn">
        <span class="num">{{ enAlerta().length }}</span>
        <span class="lbl">Por vencer (en alerta)</span>
      </div>
      <div class="tile">
        <span class="num">{{ alertas().length }}</span>
        <span class="lbl">Contratos activos</span>
      </div>
    </div>

    @if (alertas().length) {
      <div class="tabla-wrap">
        <table class="tabla">
          <thead>
            <tr>
              <th>N° contrato</th>
              <th>Administradora</th>
              <th>Vence</th>
              <th>Días restantes</th>
              <th>Estado alerta</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            @for (a of alertas(); track a.id) {
              <tr [class.fila-vencido]="a.vencido" [class.fila-alerta]="a.en_alerta && !a.vencido">
                <td>{{ a.numero_contrato }}</td>
                <td>{{ a.administradora }}</td>
                <td>{{ a.fecha_fin }}</td>
                <td>
                  @if (a.dias_para_vencer !== null) {
                    {{ a.dias_para_vencer }}
                  } @else {
                    —
                  }
                </td>
                <td>
                  @if (a.vencido) {
                    <span class="chip chip-no">Vencido</span>
                  } @else if (a.en_alerta) {
                    <span class="chip chip-no">En alerta ({{ a.dias_previos }}d)</span>
                  } @else if (a.alerta_activa) {
                    <span class="chip chip-ok">Vigente</span>
                  } @else {
                    <span class="chip chip-teal">Sin alerta</span>
                  }
                </td>
                <td><a [routerLink]="['/contratos', a.id]" class="btn btn-outline btn-sm">Ver</a></td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    } @else {
      <p class="vacio">No hay contratos activos.</p>
    }
  `,
  styles: [`
    .resumen { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
    .tile {
      flex: 1;
      min-width: 150px;
      background: #fff;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 1rem 1.2rem;
      display: flex;
      flex-direction: column;
    }
    .tile .num { font-size: 1.8rem; font-weight: 700; color: var(--navy); }
    .tile .lbl { font-size: 0.82rem; color: var(--muted); }
    .tile-danger { border-color: #f3c1c1; }
    .tile-danger .num { color: var(--danger); }
    .tile-warn { border-color: #f0d9a8; }
    .tile-warn .num { color: #b45309; }
    .fila-vencido { background: #fdeaea !important; }
    .fila-alerta { background: #fff7e6 !important; }
    .vacio { color: var(--muted); }
  `],
})
export class AlertasComponent implements OnInit {
  private api = inject(ApiService);

  alertas = signal<AlertaResumen[]>([]);
  vencidos = computed(() => this.alertas().filter((a) => a.vencido));
  enAlerta = computed(() => this.alertas().filter((a) => a.en_alerta && !a.vencido));

  ngOnInit(): void {
    this.api.getAlertas().subscribe((a) => this.alertas.set(a));
  }
}
