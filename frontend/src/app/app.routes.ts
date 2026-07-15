import { Routes } from '@angular/router';
import { SearchBarComponent } from './components/search-bar/search-bar.component';
import { ContractDetailComponent } from './components/contract-detail/contract-detail.component';

export const routes: Routes = [
  { path: '', component: SearchBarComponent },
  { path: 'contratos/:id', component: ContractDetailComponent },
  { path: '**', redirectTo: '' },
];
