
import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Observable, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, takeUntil, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ApiService, Contrato } from '../../services/api.service';

@Component({
  selector: 'app-search-bar',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './search-bar.component.html',
  styleUrls: ['./search-bar.scss']
})
export class SearchBarComponent implements OnInit, OnDestroy {
  searchControl = new FormControl('');
  resultados$!: Observable<Contrato[]>;
  isLoading = false;
  private destroy$ = new Subject<void>();

  constructor(private router: Router, private apiService: ApiService) {}

  ngOnInit(): void {
    this.resultados$ = this.searchControl.valueChanges.pipe(
      takeUntil(this.destroy$),
      debounceTime(300),
      distinctUntilChanged(),
      tap(() => this.isLoading = true),
      switchMap((termino: string | null) => this.apiService.buscarContratos(termino || '')),
      tap(() => this.isLoading = false)
    );
  }

  seleccionarContrato(contratoId: number): void {
    this.router.navigate(['/contratos', contratoId]);
    this.searchControl.setValue('', { emitEvent: false });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
