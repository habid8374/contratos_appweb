import { Component, OnInit, OnDestroy, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, of, switchMap, takeUntil, tap } from 'rxjs';
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
  consultando = signal(false);
  hayBusqueda = signal(false);

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
    });

    // No se carga todo el catálogo: se consulta por código/descripción.
    this.filtroTarifas.valueChanges
      .pipe(
        takeUntil(this.destroy$),
        debounceTime(300),
        distinctUntilChanged(),
        tap((q) => {
          const term = (q || '').trim();
          this.hayBusqueda.set(term.length >= 2);
          this.consultando.set(term.length >= 2);
          if (term.length < 2) {
            this.tarifas.set([]);
          }
        }),
        switchMap((q) => {
          const term = (q || '').trim();
          return term.length >= 2
            ? this.apiService.getTarifas(this.contratoId, term)
            : of([] as Tarifa[]);
        }),
      )
      .subscribe((t) => {
        this.tarifas.set(t);
        this.consultando.set(false);
      });
  }

  formatoValor(v: string | number): string {
    return Number(v).toLocaleString('es-CO');
  }

  checkAlertStatus(contrato: Contrato): void {
    if (!contrato.fecha_fin) {
      return;
    }
    // Preferir los días ya calculados por el backend; si no, calcular localmente.
    let diffDays = contrato.dias_para_vencer ?? null;
    if (diffDays === null) {
      const fechaFin = new Date(contrato.fecha_fin);
      const hoy = new Date();
      diffDays = Math.ceil((fechaFin.getTime() - hoy.getTime()) / (1000 * 60 * 60 * 24));
    }
    this.diasRestantes.set(diffDays);

    // Umbral configurado en el contrato (días previos de la alerta); 90 por defecto.
    const umbral =
      contrato.alerta?.activa && contrato.alerta?.dias_previos
        ? contrato.alerta.dias_previos
        : 90;

    if (diffDays <= umbral) {
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
