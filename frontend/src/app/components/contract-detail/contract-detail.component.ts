import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, switchMap, takeUntil } from 'rxjs';
import { ApiService, Contrato, Tarifa } from '../../services/api.service';

@Component({
  selector: 'app-contract-detail',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './contract-detail.component.html',
  styleUrls: ['./contract-detail.scss'],
})
export class ContractDetailComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private apiService = inject(ApiService);

  contrato = signal<Contrato | null>(null);
  tarifas = signal<Tarifa[]>([]);
  diasRestantes = signal<number | null>(null);
  alertaCritica = signal(false);

  filtroTarifas = new FormControl('', { nonNullable: true });

  private contratoId = 0;
  private destroy$ = new Subject<void>();

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.contratoId = Number(params.get('id'));
      this.apiService.getContratoDetalle(this.contratoId).subscribe({
        next: (contrato) => {
          this.contrato.set(contrato);
          this.checkAlertStatus(contrato);
        },
        error: (err) =>
          console.warn(`No se pudo cargar el contrato ${this.contratoId}.`, err?.message ?? err),
      });
      this.cargarTarifas('');
    });

    this.filtroTarifas.valueChanges
      .pipe(
        takeUntil(this.destroy$),
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((q) => this.apiService.getTarifas(this.contratoId, q || '')),
      )
      .subscribe((t) => this.tarifas.set(t));
  }

  private cargarTarifas(q: string): void {
    this.apiService.getTarifas(this.contratoId, q).subscribe({
      next: (t) => this.tarifas.set(t),
      error: () => this.tarifas.set([]),
    });
  }

  checkAlertStatus(contrato: Contrato): void {
    if (!contrato.fecha_fin) {
      return;
    }
    const fechaFin = new Date(contrato.fecha_fin);
    const hoy = new Date();
    const diffDays = Math.ceil((fechaFin.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24));
    this.diasRestantes.set(diffDays);

    if (diffDays <= 90) {
      this.alertaCritica.set(true);
      this.reproducirAlerta();
    }
  }

  /** Beep de alerta generado con Web Audio API (sin archivo de audio, SSR-safe). */
  private reproducirAlerta(): void {
    if (typeof window === 'undefined' || !('AudioContext' in window)) {
      return;
    }
    try {
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'sine';
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.6);
      osc.connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.6);
    } catch {
      // El navegador puede bloquear el audio hasta que haya interacción del usuario.
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
