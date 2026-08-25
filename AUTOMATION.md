# Plan semanal automático (Garmin → Claude → app)

Cada **domingo a las 20:00 (hora de Galicia)** un cron gratuito en GitHub
Actions:

1. Lee tus métricas de recuperación de los últimos 7 días de **Garmin** (HRV,
   sueño, readiness, carga de entrenamiento, FC en reposo).
2. Se las pasa a **Claude** —usando tu suscripción **Pro** vía Claude Code
   headless, sin factura de API— que actúa de entrenador y genera el plan de
   los próximos 7 días.
3. Escribe ese plan en tu cuenta (tabla `planned_workouts`), y lo ves en **HOY**
   como "Hoy toca …".

```
GitHub Actions (dom 20:00) ─▶ app/automation/weekly_plan.py
        │                          │  1. Garmin  (garminconnect + tokens)
        │                          │  2. Claude  (claude -p, tu Pro)
        │                          ▼
        └──────────────────▶  Neon (planned_workouts)  ─▶  se ve en HOY
```

**Coste: 0 €.** Actions es gratis, Neon es gratis, y la IA va dentro de tu Pro.

Si un domingo falla, **GitHub te manda un email** automáticamente. Para
relanzarlo a mano: repo → **Actions → Weekly plan → Run workflow**.

---

## Puesta en marcha (una vez, ~15 min)

Todo son **4 secretos** que configuras tú en GitHub
(*Settings → Secrets and variables → Actions → New repository secret*).
Nunca pegues credenciales en el chat ni en el código.

### 1. `DATABASE_URL` — tu base de datos Neon

El mismo connection string que ya usas en `infra/terraform/terraform.tfvars`
(`postgresql+psycopg://…neon.tech/…?sslmode=require`).

### 2. `PLAN_USER_EMAIL` — a qué cuenta escribir

Tu email de la app (p. ej. `hermida95@gmail.com`).

### 3. `CLAUDE_CODE_OAUTH_TOKEN` — usar tu Claude Pro sin pagar API

En tu Mac, con Claude Code instalado y tu sesión Pro iniciada:

```bash
claude setup-token
```

Genera un token de larga duración pensado para CI. Copia el valor y pégalo en
el secreto. (Corre dentro de los límites de tu plan Pro; una generación
semanal es insignificante.)

### 4. `GARMIN_TOKENS_B64` — tus tokens de Garmin (sin contraseña en el cron)

Son los **mismos tokens que ya usa tu MCP de Garmin** (`~/.garminconnect/
garmin_tokens.json`). Confirmado: con `garminconnect==0.3.2` funcionan tal
cual, **no hace falta volver a loguearse**. Solo hay que empaquetarlos y
meterlos como secreto. En tu Mac:

```bash
# Comprueba que está el fichero de tokens:
ls "$HOME/.garminconnect"        # deberías ver garmin_tokens.json

# Empaqueta y codifica en base64, y déjalo en el portapapeles (macOS):
tar -czf - -C "$HOME/.garminconnect" . | base64 | pbcopy
```

`pbcopy` deja el base64 en el portapapeles: pégalo en el secreto
`GARMIN_TOKENS_B64`. El workflow lo descodifica en cada ejecución a
`~/.garminconnect`.

> Cuando los tokens caduquen (~6 meses) o dejen de funcionar, vuelve a
> generarlos con tu MCP/login de Garmin y repite este paso.

---

## Probarlo sin esperar al domingo

- **A mano en GitHub**: Actions → *Weekly plan* → **Run workflow** (trae el
  input *force* activado, así ignora el guard horario y corre ya).
- **En tu Mac** (con el venv del backend y `claude` disponible):

  ```bash
  cd backend
  # Solo prueba el pipeline, sin escribir en la BD y con métricas de ejemplo:
  DATABASE_URL="sqlite:///./local.db" \
    python -m app.automation.weekly_plan tu@email.com --force --dry-run --stub-metrics

  # Con tus métricas reales de Garmin (necesita los tokens en ~/.garminconnect):
  DATABASE_URL="sqlite:///./local.db" \
    python -m app.automation.weekly_plan tu@email.com --force --dry-run
  ```

Flags: `--force` (ignora el guard horario), `--dry-run` (no escribe, solo
imprime el plan), `--stub-metrics` (métricas de ejemplo, sin Garmin).

---

## Cómo decide el plan

El *system prompt* (en `app/automation/coach.py`) le da a Claude tu contexto:
plan híbrido Fuerza + Trail/Ultra, estructura Lun/Mié/Vie gym + Mar/Jue/Sáb
running + domingo descanso, reglas 80/20 y descarga cada 4 semanas. Claude
**ajusta la carga** según tus métricas: si HRV/readiness/sueño están bajos o la
carga aguda alta, baja volumen e intensidad (más Z2, menos series, o convierte
un rodaje en descanso); si están altos, progresa con prudencia. No inventa
listas de ejercicios —esos ya están en tu rutina de la app—, decide el
**enfoque y los tiempos**.

El JSON que devuelve Claude se valida antes de escribir (7 días, tipos válidos,
título presente) y se reintenta una vez si no cuadra.

## Cambiar el horario o el enfoque

- **Horario**: edita los dos `cron` de `.github/workflows/weekly-plan.yml`
  (van en UTC; el par de horas cubre el horario de verano/invierno) y la
  ventana en `should_run_now()` de `weekly_plan.py`.
- **Criterio del coach**: edita `SYSTEM_CONTEXT` en `app/automation/coach.py`.
