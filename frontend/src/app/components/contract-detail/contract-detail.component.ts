
import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { CommonModule } from '@angular/common';
import { ApiService, Contrato } from '../../services/api.service';

@Component({
  selector: 'app-contract-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './contract-detail.component.html',
  styleUrls: ['./contract-detail.scss']
})
export class ContractDetailComponent implements OnInit, OnDestroy {
  contrato: Contrato | null = null;
  alertaCritica = false;
  private destroy$ = new Subject<void>();
  private audio: HTMLAudioElement;

  constructor(private route: ActivatedRoute, private apiService: ApiService) {
    this.audio = new Audio('assets/sounds/alert.mp3');
    this.audio.load();
  }

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntil(this.destroy$)).subscribe(params => {
      const id = Number(params.get('id'));
      this.apiService.getContratoDetalle(id).subscribe(contrato => {
        this.contrato = contrato;
        this.checkAlertStatus(contrato);
      });
    });
  }

  checkAlertStatus(contrato: Contrato): void {
    if (!contrato.fecha_fin) {
      return;
    }

    const fechaFin = new Date(contrato.fecha_fin);
    const hoy = new Date();
    const diffTime = fechaFin.getTime() - hoy.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    if (diffDays <= 90) {
      this.alertaCritica = true;
      this.playAlertSound();
    }
  }

  async playAlertSound(): Promise<void> {
    try {
      await this.audio.play();
    } catch (err) {
      console.warn('Reproducción de audio bloqueada por el navegador.', err);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.audio) {
      this.audio.pause();
    }
  }
}
