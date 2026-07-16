import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { switchMap } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent {
  private fb = inject(FormBuilder);
  private auth = inject(AuthService);
  private router = inject(Router);

  form = this.fb.nonNullable.group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  cargando = signal(false);
  error = signal<string | null>(null);

  enviar(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.cargando.set(true);
    this.error.set(null);
    const { username, password } = this.form.getRawValue();

    this.auth
      .login(username, password)
      .pipe(switchMap(() => this.auth.cargarUsuario()))
      .subscribe({
        next: () => {
          this.cargando.set(false);
          this.router.navigate(['/']);
        },
        error: () => {
          this.cargando.set(false);
          this.error.set('Usuario o contraseña incorrectos.');
        },
      });
  }
}
