import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

interface Accion {
  titulo: string;
  descripcion: string;
  ruta: string;
  icono: string;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent {
  protected auth = inject(AuthService);

  acciones: Accion[] = [
    {
      titulo: 'Administradoras / EPS',
      descripcion: 'Crea y configura administradoras y sus contratos.',
      ruta: '/administradoras',
      icono: '🏢',
    },
    {
      titulo: 'Control PGP',
      descripcion: 'Seguimiento del consumo vs la nota técnica de contratos PGP.',
      ruta: '/pgp',
      icono: '📊',
    },
    {
      titulo: 'Alertas de vencimiento',
      descripcion: 'Contratos por vencer y vencidos, según los días configurados.',
      ruta: '/alertas',
      icono: '⏰',
    },
    {
      titulo: 'Buscar contratos',
      descripcion: 'Consulta contratos por administradora, NIT o número.',
      ruta: '/buscar',
      icono: '🔍',
    },
    {
      titulo: 'Cargar anexo de tarifas',
      descripcion: 'Sube un Excel de tarifas y actualiza los datos del contrato.',
      ruta: '/cargar',
      icono: '📤',
    },
  ];
}
