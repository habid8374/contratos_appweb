import { Routes } from '@angular/router';
import { authGuard } from './guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () =>
      import('./components/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/dashboard/dashboard.component').then((m) => m.DashboardComponent),
  },
  {
    path: 'buscar',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/search-bar/search-bar.component').then((m) => m.SearchBarComponent),
  },
  {
    path: 'cargar',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/anexo-upload/anexo-upload.component').then(
        (m) => m.AnexoUploadComponent,
      ),
  },
  {
    path: 'contratos/:id',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./components/contract-detail/contract-detail.component').then(
        (m) => m.ContractDetailComponent,
      ),
  },
  { path: '**', redirectTo: '' },
];
