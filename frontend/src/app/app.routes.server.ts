import { RenderMode, ServerRoute } from '@angular/ssr';

export const serverRoutes: ServerRoute[] = [
  {
    // Rutas con autenticación y datos dinámicos: render en servidor, sin prerender.
    path: '**',
    renderMode: RenderMode.Server,
  },
];
