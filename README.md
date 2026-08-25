# CIMA

[![CI](https://github.com/Hermida95/training-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/Hermida95/training-tracker/actions/workflows/ci.yml)
[![Deploy](https://github.com/Hermida95/training-tracker/actions/workflows/deploy.yml/badge.svg)](https://github.com/Hermida95/training-tracker/actions/workflows/deploy.yml)

PWA full-stack de entreno híbrido fuerza + trail/ultra: rutina de gimnasio
editable con periodización, checklist diario con rachas y puntos, plan semanal
generado por un coach IA a partir de tus métricas de Garmin, métricas
corporales con media semanal, alarma antisedentarismo con notificaciones
programadas, plan de comidas y cuentas multiusuario. Diseño de marca "gear
técnico de montaña" — naranja señal sobre carbón, tipografía de cartelería de
sendero — pensada para usarse con el pulgar entre series.

> Nota: el repositorio de GitHub sigue llamándose `training-tracker` (cambiar
> el nombre del repo rompería las URLs de Cloud Run ya desplegadas); CIMA es
> el nombre de marca de la app en sí, no del repo.

**Stack**: Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Alembic ·
PostgreSQL &nbsp;|&nbsp; React 18 · Vite · TypeScript · PWA + Service Worker
&nbsp;|&nbsp; Docker · Terraform · GCP Cloud Run · GitHub Actions (push a main = deploy)

## Funcionalidades

- 🏋️ **Entreno**: rutina precargada editable (cada usuario construye la suya:
  añade/quita ejercicios, pesos, series), **autoguardado ejercicio a ejercicio**
  (si la app se cierra a media sesión no se pierde nada), registro de series en
  2 toques, comparación con la sesión anterior y periodización S1 RIR 3 → S4
  descarga visible en la UI. Las sesiones de gym pueden **marcarse hechas de un
  toque** (sin registrar, para los días que ya lo llevas en el reloj) y los
  rodajes de running se marcan hechos directamente
- 🎯 **Planes por usuario**: la rutina y hábitos de una cuenta se pueden ajustar
  a un plan concreto con un script versionado sin tocar el seed por defecto
  (ver `app/seed/hybrid_plan.py`, aplicable con `python -m app.seed.hybrid_plan <email>`)
- ✅ **Hábitos**: pantalla HOY gamificada con aro de progreso, racha y tira de la
  semana; checklist según el día, hábitos personalizables (booleanos o con
  objetivo numérico), **edición de días pasados** y puntuación diaria por niveles
- 🤖 **Plan semanal automático** (opcional): un cron gratuito los domingos lee
  tus métricas de recuperación de Garmin, se las pasa a Claude como entrenador
  y escribe el plan de la semana siguiente por día, que ves en HOY como "Hoy
  toca …". Detalle y puesta en marcha en [AUTOMATION.md](AUTOMATION.md)
- 📈 **Progreso**: peso y cintura con media móvil semanal (recharts), resumen
  mensual y export JSON/texto para pegar a un coach IA
- ⏰ **Alarma antisedentarismo**: notificaciones locales programadas cada 45-50
  min (L-V, 08:30-15:00 Europe/Madrid) que funcionan con el móvil bloqueado,
  con acciones "Hecho" / "Posponer 5 min"
- 🍴 **Menú**: sube tu plan de comidas (foto/PDF/texto) y tenlo siempre a mano
- 🔐 **Multiusuario**: cuentas con JWT, datos completamente aislados por usuario,
  registro cerrado con códigos de invitación que reparte el administrador,
  recuperación de contraseña sin email (código de un solo uso), rate limiting
  y auditoría de seguridad documentada

```
training-tracker/
├── backend/             FastAPI, modelos, migraciones, tests (pytest)
├── frontend/            React + Vite + service worker
├── infra/terraform/     IaC para GCP: Cloud Run, secretos, Workload Identity
├── docker-compose.yml   Entorno local completo (db + api + front)
├── .github/workflows/   CI (lint + tests) y CD (deploy a Cloud Run)
├── DEPLOY.md            Guía de despliegue 0€/mes (Neon + Cloud Run)
└── SECURITY.md          Auditoría de seguridad y riesgos aceptados
```

## Arranque local

```bash
cp .env.example .env
docker compose up --build
```

- Front: http://localhost:5173
- API: http://localhost:8000 · docs autogeneradas en http://localhost:8000/docs (Swagger) y `/redoc`
- La API aplica migraciones (`alembic upgrade head`) en cada arranque del contenedor.
- La primera pantalla es el login: crea tu cuenta y arrancarás con la rutina GYM 1/2/3 y los
  hábitos base ya sembrados (la siembra es por usuario, en el registro).

Sin Docker, cada servicio arranca suelto:

```bash
# backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
DATABASE_URL=sqlite:///./local.db alembic upgrade head
DATABASE_URL=sqlite:///./local.db uvicorn app.main:app --reload

# frontend
cd frontend && npm install && npm run dev
```

## Tests y lint

```bash
cd backend && pytest -v && ruff check . && ruff format --check .
cd frontend && npm run lint && npm run typecheck && npm run build
```

CI (`.github/workflows/ci.yml`) corre exactamente estos comandos en cada push/PR.

---

## Decisiones de arquitectura

**Multiusuario con JWT.** Cada cuenta (email + contraseña) tiene sus propios hábitos, entrenos,
métricas, pausas y ajustes: todas las tablas de datos llevan `user_id` y cada endpoint filtra por
el usuario del token. El login es JWT firmado con `SECRET_KEY` (HS256, 30 días de validez, pensado
para no reloguear en el gym) con la contraseña hasheada con bcrypt. El token viaja en
`Authorization: Bearer` — también desde el service worker, que lo recibe por `postMessage` porque
no puede leer el localStorage de la página. Al registrarse, `seed_user()` crea la copia personal
de la rutina GYM 1/2/3 y los hábitos base, que cada usuario puede editar sin afectar al resto.
En producción, `SECRET_KEY` debe venir de Secret Manager (ver sección de despliegue).

**Hábitos como filas genéricas, no una tabla por hábito.** `Habit` tiene `value_type`
(`boolean`/`numeric`) y `active_days` (qué días de la semana aplica). Esto permite modelar tanto
"McGill Big 3" (booleano, L/X/V) como "10.000 pasos" (numérico con objetivo, todos los días) con
el mismo esquema, en vez de tablas o columnas especiales por hábito. Ver
[`app/models/habit.py`](backend/app/models/habit.py) y la siembra en
[`app/seed/seed_data.py`](backend/app/seed/seed_data.py).

**Rachas (streaks) calculadas, no almacenadas.** `current_streak` se recalcula en cada request
(`app/utils/streak.py`) recorriendo `habit_logs` hacia atrás desde hoy, saltando días en los que
el hábito no aplicaba. Es más simple y menos propenso a bugs de sincronización que mantener un
contador desnormalizado que hay que acordarse de actualizar en cada escritura. Con el volumen de
datos de una app personal, el coste de recalcular es insignificante.

**Periodización basada en fecha, no en un contador de sesiones.** El ciclo de 4 semanas
(`app/utils/periodization.py`) se ancla a una fecha de inicio guardada en `app_settings`
(`program_start_date`, por defecto el lunes de la semana del primer uso) y se deriva con
`(días transcurridos // 7) % 4`. Así, si te saltas una semana, el ciclo sigue avanzando con el
calendario en vez de "esperarte" — que es el comportamiento que se espera de un programa de
fuerza con progresión semanal real.

**Snapshots de nombre de ejercicio, no solo el ID de plantilla.** `WorkoutExercise.name` guarda
una copia del nombre en el momento de la sesión, además de la FK opcional a `ExerciseTemplate`.
Si más adelante renombras o borras un ejercicio de la rutina precargada, las sesiones históricas
no cambian ni se rompen.

**La comparación con la sesión anterior empareja por nombre + número de serie**
(`app/utils/comparison.py`), no por posición en un array. Si añades un ejercicio nuevo a mitad de
rutina, el resto de comparaciones no se desplazan ni se corrompen — simplemente esa serie nueva no
tiene "anterior" (`delta = null`).

---

## Estrategia de notificaciones (PWA + service worker)

Objetivo: avisar cada 45-50 min, solo L-V 08:30-15:00 Europe/Madrid, **con el móvil bloqueado**.
Esto es el punto más delicado de todo el proyecto porque un service worker no es un proceso
siempre activo — el navegador lo apaga en cuanto no tiene trabajo pendiente, así que un
`setTimeout` de 45 minutos casi nunca sobrevive.

La implementación completa y muy comentada está en [`frontend/public/sw.js`](frontend/public/sw.js)
(léelo, tiene un bloque de comentarios largo explicando cada decisión). Resumen:

### Nivel 1 — Notification Triggers API (mejor caso)

```js
registration.showNotification(title, {
  showTrigger: new TimestampTrigger(timestamp),
  actions: [{ action: "done", title: "Hecho ✅" }, { action: "postpone", title: "Posponer 5 min" }],
});
```

Es la API diseñada exactamente para esto: le dices al **navegador** que muestre una notificación
en un instante futuro, y es el navegador quien la dispara — no tu JavaScript, que puede llevar
horas dormido. Funciona con el móvil bloqueado y la app cerrada.

**Soporte real (2026):** Chrome/Edge en Android (parcial, algunos requieren activar el flag
`chrome://flags/#notification-triggers`). **No soportado** en iOS Safari ni Firefox. Por eso se usa
con *feature detection* (`'showTrigger' in Notification.prototype`) como mejora progresiva, nunca
como único camino.

### Nivel 2 — Fallback en la página (mientras la app está abierta)

Si el navegador no soporta Triggers, [`useNotificationScheduler.ts`](frontend/src/hooks/useNotificationScheduler.ts)
mantiene un `setTimeout` en el hilo principal que llama a `registration.showNotification()` sin
trigger. Cubre el caso más común en la práctica — llevas la PWA abierta durante la jornada — pero
**no** sobrevive a bloquear el móvil con la app completamente cerrada.

### Nivel 3 — Web Push (el camino "a prueba de balas", documentado pero no implementado)

La única forma 100% fiable en cualquier navegador de despertar el dispositivo con la app cerrada
y el móvil bloqueado es exactamente lo que hace WhatsApp: **Web Push real**. Un servidor manda un
push firmado (claves VAPID) en cada instante programado, y es el sistema operativo — FCM en
Android/Chrome, APNs en iOS 16.4+ para PWAs instaladas — quien despierta el service worker
mediante el evento `push`, sin depender de que el navegador siga vivo.

No se implementa en este repo para no meter infraestructura no pedida, pero si quieres el nivel
de fiabilidad de una app nativa, el plan es:

1. Backend genera un par de claves VAPID (`web-push` o similar) y las expone en un endpoint.
2. Frontend hace `pushManager.subscribe()` y manda la `PushSubscription` a un nuevo endpoint
   `POST /api/v1/push-subscriptions`.
3. Un Cloud Scheduler (cron, ver `infra/terraform`) llama cada 5 min a un endpoint
   `POST /api/v1/breaks/dispatch` que calcula si "ahora" cae dentro de la ventana/intervalo de
   algún usuario y, si es así, envía el push a su subscription.
4. `sw.js` ya tiene la estructura lista para añadir un listener `self.addEventListener('push', ...)`
   que muestre la notificación con los mismos botones de acción.

### Persistencia de config en el service worker

Un SW no tiene `localStorage` fiable entre reinicios (el navegador lo mata y recrea). La config
(URL de la API, intervalo, ventana horaria) se guarda con la **Cache Storage API** simulando un
key-value store (`saveConfig`/`loadConfig` en `sw.js`), que sí sobrevive a que el navegador
recicle el proceso del SW.

### Cálculo de horarios en Europe/Madrid sin librerías

`sw.js` y `src/notifications/scheduleMath.ts` calculan a mano, con `Intl.DateTimeFormat`, el
instante UTC exacto que corresponde a "08:30 en Madrid" ese día concreto — necesario porque Madrid
cambia de UTC+1 a UTC+2 en el cambio de hora y una alarma fija en UTC se desincronizaría dos veces
al año. El truco (`zonedWallTimeToUtc`): se construye una fecha UTC "adivinada" y se corrige con el
offset real de esa zona en ese instante.

---

## Despliegue en GCP Cloud Run — paso a paso

> **La guía definitiva y actualizada está en [DEPLOY.md](DEPLOY.md)**: Neon +
> Terraform + despliegue automático con GitHub Actions (push a main = deploy,
> sin claves guardadas gracias a Workload Identity, ver
> `infra/terraform/cicd.tf`). Lo de abajo es la variante manual con gcloud,
> útil para entender qué hace cada pieza por dentro.

### 0. Prerrequisitos

```bash
gcloud auth login
gcloud config set project TU_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com sqladmin.googleapis.com
```

### 1. Construir y subir las imágenes

Primero crea el repo de Artifact Registry (o hazlo con Terraform, ver paso 3, y sube las imágenes
después):

```bash
REGION=europe-southwest1
PROJECT_ID=tu-project-id
REPO=training-tracker

gcloud artifacts repositories create $REPO --repository-format=docker --location=$REGION

gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Backend (arquitectura amd64: Cloud Run no corre imágenes arm64 de tu Mac M-series)
docker build --platform linux/amd64 --target production \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest ./backend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest

# Frontend: VITE_API_BASE_URL se hornea en build-time. La primera vez no
# conoces la URL final de la API, así que usa una ruta relativa /api/v1 y
# pon un proxy en Cloud Run, o simplemente reconstruye el front una vez
# tengas la URL real de la API (paso 4).
docker build --platform linux/amd64 --target production \
  --build-arg VITE_API_BASE_URL=https://PLACEHOLDER/api/v1 \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/front:latest ./frontend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/front:latest
```

### 2. Base de datos: Cloud SQL o alternativa gratuita

**Opción A — Cloud SQL** (gestionado por el Terraform de este repo, ver más abajo). Tiene coste
(aunque `db-f1-micro` es barato, no hay free tier permanente de Cloud SQL).

**Opción B — Neon o Supabase (Postgres gratuito)**, recomendado para un proyecto personal:

1. Crea una cuenta en [neon.tech](https://neon.tech) o [supabase.com](https://supabase.com) y un proyecto Postgres.
2. Copia el connection string que te dan (formato `postgresql://user:pass@host/db?sslmode=require`)
   y cámbialo a `postgresql+psycopg://...` (SQLAlchemy necesita el driver en el scheme).
3. En Terraform, usa `use_cloud_sql = false` y `external_database_url = "esa URL"` (ver
   `infra/terraform/terraform.tfvars.example`). Cloud Run no necesita ningún volumen ni permiso
   especial para hablar con Neon/Supabase: es una conexión TLS normal por internet.

### 3. Desplegar con Terraform

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
# edita terraform.tfvars: project_id, api_image, front_image, use_cloud_sql...

terraform init
terraform plan    # revisa qué se va a crear antes de aplicar
terraform apply
```

Esto crea: Artifact Registry, (opcionalmente) Cloud SQL + base de datos + usuario, el secreto de
`DATABASE_URL`, la service account del backend, los dos servicios de Cloud Run y los permisos para
que sean públicos. Cada recurso está comentado línea a línea en su fichero — empieza por
[`infra/terraform/README` más abajo](#mapa-del-terraform) para saber dónde mirar cada cosa.

Al terminar, `terraform output` imprime `api_url` y `front_url`.

### 4. Segunda vuelta: conectar el front con la URL real de la API

Cloud Run asigna la URL del backend en el primer `apply` (problema típico de huevo-y-gallina: no
puedes hornear `VITE_API_BASE_URL` en el bundle del front antes de que la API exista). Con la
`api_url` del output:

```bash
docker build --platform linux/amd64 --target production \
  --build-arg VITE_API_BASE_URL=${API_URL}/api/v1 \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/front:latest ./frontend
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/front:latest

# y opcionalmente fija cors_origin = "https://tu-front-url" en terraform.tfvars
terraform apply
```

Cloud Run despliega automáticamente una nueva revisión al detectar que el tag de la imagen
apunta a un digest distinto — no hace falta ningún paso manual extra de "redeploy".

### CI/CD (ampliación sugerida, no incluida)

El workflow actual (`.github/workflows/ci.yml`) solo hace lint + tests. Para automatizar el
despliegue, añade un segundo job en `main` que haga `docker build && push` + `terraform apply`
usando una service account de GitHub Actions con permisos mínimos (Artifact Registry Writer +
Cloud Run Admin + Service Account User), autenticada vía Workload Identity Federation en vez de
una clave JSON descargada.

---

## Mapa del Terraform

| Fichero | Qué crea | Por qué existe |
|---|---|---|
| `versions.tf` / `providers.tf` | Versión de Terraform y del provider de Google | Reproducibilidad: mismo comportamiento hoy y dentro de 6 meses |
| `apis.tf` | Habilita las APIs de GCP necesarias | Un proyecto nuevo las tiene todas apagadas |
| `artifact_registry.tf` | Repo Docker | Dónde viven las imágenes de `api` y `front` |
| `cloud_sql.tf` | Instancia Postgres + BD + usuario (condicional) | Base de datos gestionada, solo si `use_cloud_sql = true` |
| `secrets.tf` | Secret Manager con `DATABASE_URL` | La contraseña de la BD nunca queda en texto plano en la config del servicio |
| `service_accounts.tf` | Identidad dedicada para el backend | Principio de menor privilegio, en vez de la SA de Compute Engine por defecto |
| `iam.tf` | Quién puede leer el secreto / invocar los servicios | Cloud Run público + acceso mínimo al secreto |
| `cloud_run_api.tf` | Servicio Cloud Run del backend | Incluye el volumen especial para el proxy de Cloud SQL |
| `cloud_run_front.tf` | Servicio Cloud Run del frontend | nginx sirviendo el bundle estático |
| `outputs.tf` | URLs finales | Para no ir a buscarlas a la consola |

Cada recurso individual tiene un comentario explicando qué es y por qué está ahí — es la parte
pensada para aprender Terraform leyendo, no solo para copiar y pegar.

---

## API

Todos los endpoints viven bajo `/api/v1` (ver `backend/app/api/v1/`). Documentación autogenerada
por FastAPI en `/docs` (Swagger UI) y `/redoc`. Resumen:

- `/habits`, `/habits/today`, `/habits/{id}/logs` — CRUD de hábitos + registro diario + racha calculada
- `/workouts`, `/workouts/templates`, `/workouts/{id}/comparison`, `/workouts/periodization` — sesiones, rutina precargada, comparación con la sesión anterior, semana del ciclo de 4
- `/body-metrics`, `/body-metrics/weekly-average` — peso/cintura + media móvil semanal
- `/breaks`, `/breaks/config` — pausas activas y configuración de la alarma
- `/menu` — el plan de comidas del usuario: sube foto/PDF (máx. 8MB, guardado en la BD)
  o texto pegado; `/menu/{id}/file` sirve el binario con el token
- `/stats/monthly` — resumen del mes
- `/export?format=json|text` — resumen del mes listo para pegar a un coach IA

La auditoría de seguridad pre-despliegue, con los riesgos aceptados y el
checklist de producción, está en [SECURITY.md](SECURITY.md).

La inyección de la sesión de BD se hace con el patrón `Depends(get_db)` de FastAPI
(`app/core/deps.py`), y cada módulo de `app/crud/` concentra las queries de un dominio, separado
de la capa HTTP en `app/api/v1/endpoints/`.
