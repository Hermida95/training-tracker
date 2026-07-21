# Seguridad

**¿Has encontrado una vulnerabilidad?** Abre un
[Security Advisory privado](https://github.com/Hermida95/training-tracker/security/advisories/new)
en vez de un issue público. Gracias.

---

## Auditoría de seguridad

Revisión hecha sobre el código completo (API, frontend, service worker, infra)
antes del primer despliegue público. Formato: qué se comprobó, qué se corrigió
y qué riesgos quedan aceptados a sabiendas.

## Comprobado y correcto

| Área | Estado |
|---|---|
| Inyección SQL | Todo el acceso a datos usa SQLAlchemy con parámetros ligados; no hay SQL construido con strings. |
| IDOR (acceso a datos de otros) | Todas las tablas llevan `user_id`; cada endpoint resuelve el recurso **y comprueba el propietario**, devolviendo 404 (no 403, para no confirmar que el recurso existe). Cubierto por tests de aislamiento (`test_auth.py`, `test_menu.py`). |
| Contraseñas | Hasheadas con bcrypt (salt por hash). Nunca se devuelven ni se loguean. Mínimo 8 caracteres, máximo 72 (límite real de bcrypt, para evitar truncado silencioso). |
| JWT | HS256 con algoritmo fijado también al decodificar (sin confusión de algoritmo), expiración de 30 días, `sub` = user id. La clave de firma va en Secret Manager en producción. |
| Enumeración de usuarios en login | Mismo mensaje de error exista o no el email. |
| CORS | Lista blanca explícita de orígenes por variable de entorno; nunca `*` con credenciales. En producción debe ser exactamente la URL del frontend. |
| Subida de ficheros (menú) | Lista blanca cerrada de tipos (JPG/PNG/WebP/PDF — **SVG excluido a propósito**: puede ejecutar scripts), límite de 8MB comprobado en servidor, servido con `X-Content-Type-Options: nosniff` y `Content-Disposition: inline` con nombre controlado por el servidor. |
| Fugas en errores | FastAPI no expone stack traces en producción; el `/health` no revela entorno ni versiones. |

## Corregido durante la auditoría

1. **Arranque con clave por defecto**: la API ahora se niega a arrancar si
   `ENVIRONMENT=production` y `SECRET_KEY` sigue siendo la de desarrollo
   (`app/main.py`). Antes habría arrancado firmando tokens con una clave pública en el repo.
2. **Fuerza bruta en login/registro**: rate limit de 10 intentos/minuto por IP
   en `/auth/*` (`app/core/rate_limit.py`). Es en memoria y por instancia —
   suficiente para esta escala; el salto a Redis está documentado en el propio módulo.
3. **Cabeceras defensivas** en todas las respuestas de la API:
   `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`.
4. **Truncado de bcrypt**: contraseñas limitadas a 72 caracteres en la validación
   para que dos contraseñas largas distintas no puedan colisionar por truncado.

## Riesgos aceptados (y por qué)

- **Token en localStorage**: vulnerable a XSS si algún día se introduce una.
  Mitigado porque React escapa todo por defecto y no usamos `dangerouslySetInnerHTML`
  ni renderizamos HTML de usuario. La alternativa (cookies httpOnly) exige CSRF
  tokens y complica el service worker; no compensa a esta escala.
- **Sin revocación de tokens**: cerrar sesión solo borra el token del cliente;
  un token robado vale hasta su expiración (30 días). Aceptable en app personal.
  Si preocupa: acortar expiración o añadir una lista de revocados.
- **Sin verificación de email**: no hay envío de emails (mantenerlo gratis y
  sin servicios externos). La recuperación de contraseña se resuelve con un
  **código de recuperación de un solo uso** (hash bcrypt en BD, se muestra una
  única vez al generarlo en Ajustes) — sin código y sin contraseña, toca BD a mano.
- **Sin bloqueo de cuenta**: el rate limit por IP frena la fuerza bruta online,
  pero no hay lockout por cuenta. Con contraseñas de 8+ y bcrypt, riesgo bajo.
- **Registro por invitación**: cerrado al público. Solo se entra con un código
  de un solo uso, y **únicamente el administrador puede generarlos** (máx. 5
  pendientes). El administrador es la primera cuenta de la instancia, la del
  dueño del despliegue, que por eso es también la única que puede registrarse
  sin código. Los invitados no pueden invitar a su vez.

## Checklist antes de cada despliegue

- [ ] `SECRET_KEY` viene de Secret Manager (Terraform lo hace solo; no lo pongas en env vars planas)
- [ ] `CORS_ORIGINS` = exactamente la URL pública del frontend, sin comodines
- [ ] `ENVIRONMENT=production`
- [ ] La URL de la BD (Neon) usa `sslmode=require`
- [ ] `terraform plan` no muestra secretos en el diff que vayas a pegar en ningún sitio
