import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

/** Agrega el token Bearer a las llamadas /api y refresca una vez ante un 401. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  // No adjuntar token a los propios endpoints de login/refresh.
  const esAuthEndpoint =
    req.url.includes('/api/auth/token/') || req.url.includes('/api/auth/token/refresh/');

  const access = auth.getAccess();
  const authReq =
    access && req.url.startsWith('/api') && !esAuthEndpoint
      ? req.clone({ setHeaders: { Authorization: `Bearer ${access}` } })
      : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401 && !esAuthEndpoint && auth.getRefresh()) {
        return auth.refrescar().pipe(
          switchMap(({ access: nuevo }) =>
            next(req.clone({ setHeaders: { Authorization: `Bearer ${nuevo}` } })),
          ),
          catchError((refreshError) => {
            auth.logout();
            router.navigate(['/login']);
            return throwError(() => refreshError);
          }),
        );
      }
      return throwError(() => error);
    }),
  );
};
