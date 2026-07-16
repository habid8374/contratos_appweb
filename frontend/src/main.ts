import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';

// Mientras iteramos rápido, desregistramos cualquier service worker previo y
// limpiamos sus cachés para evitar servir chunks viejos (errores de módulos).
if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((r) => r.unregister());
  });
  if (typeof caches !== 'undefined') {
    caches.keys().then((keys) => keys.forEach((k) => caches.delete(k)));
  }
}

bootstrapApplication(App, appConfig).catch((err) => console.error(err));
