# Guía de despliegue (Neon + GCP + GitHub Actions)

Qué vas a montar, en una línea por pieza:

```
Móvil/navegador ──HTTPS──▶ Cloud Run "front" (nginx + PWA React)
                                  │ fetch
                                  ▼
                           Cloud Run "api" (FastAPI) ──▶ Neon (Postgres gratis)
                                  ▲
        GitHub Actions ───deploy──┘   (push a main = tests + build + deploy)
```

**Coste: 0 €/mes** con uso personal. Neon es gratis sin tarjeta; GCP pide
activar facturación pero Cloud Run escala a cero y su capa gratuita
(2M peticiones/mes) no se agota con una app así. Aun así, en el paso 2
configuramos una alerta de presupuesto para dormir tranquilo.

La primera vez son ~45 min siguiendo esto de arriba abajo. A partir de ahí,
**desplegar = `git push`**.

---

## 1. Base de datos en Neon (5 min)

1. Entra en [neon.tech](https://neon.tech) → *Sign up* (con GitHub mismo). No pide tarjeta.
2. *Create project* → nombre `training-tracker`, región **AWS eu-central-1 (Frankfurt)**
   (la más cercana a la región de GCP que usaremos, Madrid).
3. En el dashboard, botón *Connect* → copia el **connection string**
   (`postgresql://usuario:contraseña@ep-xxx...neon.tech/neondb?sslmode=require`).
4. **Transfórmalo** para SQLAlchemy añadiendo `+psycopg` tras `postgresql`:

   ```
   postgresql+psycopg://usuario:contraseña@ep-xxx...neon.tech/neondb?sslmode=require
   ```

   Guárdalo en un sitio seguro (gestor de contraseñas): lo usarás en el paso 4.

> Nota: el tier gratuito de Neon **suspende la BD tras unos minutos sin uso**.
> La primera petición del día tarda 2-5 s extra mientras despierta. Es normal.

## 2. Proyecto de GCP (10 min)

1. [console.cloud.google.com](https://console.cloud.google.com) → crea cuenta si no tienes
   (los nuevos reciben 300$ de crédito, aunque no los necesitarás).
2. Arriba a la izquierda → *New project* → nombre `training-tracker`. Apunta el
   **Project ID** (ej. `training-tracker-448213`; es el ID, no el nombre).
3. Activa la facturación del proyecto (*Billing*). Requisito de Cloud Run
   aunque no llegues a pagar nada.
4. Recomendado: *Billing → Budgets & alerts* → presupuesto de 5 € con aviso
   al 50/90/100%. Si algún día algo se descontrola, te llega un email antes
   de que sea un problema.
5. Instala las herramientas en tu Mac:

   ```bash
   brew install --cask google-cloud-sdk
   brew install terraform
   gcloud auth login                        # abre el navegador
   gcloud auth application-default login    # credenciales que usará Terraform
   gcloud config set project TU_PROJECT_ID
   ```

## 3. Repositorio en GitHub (5 min)

```bash
cd ~/Developer/training-tracker
gh repo create training-tracker --private --source . --push
# (o crea el repo vacío en github.com y: git remote add origin ... && git push -u origin main)
```

Apunta el nombre completo `tu-usuario/training-tracker`: el Terraform lo usa
como candado para que SOLO este repo pueda desplegar.

> El primer push ejecutará el workflow **Deploy** y fallará en el paso de
> autenticación con GCP — es lo esperado: aún no existen los secrets ni la
> infraestructura. Se arregla solo en el paso 6.

## 4. Infraestructura con Terraform (15 min)

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edita `terraform.tfvars`:

```hcl
project_id  = "TU_PROJECT_ID"
region      = "europe-southwest1"                # Madrid
github_repo = "tu-usuario/training-tracker"

use_cloud_sql         = false                    # usamos Neon, no Cloud SQL
external_database_url = "postgresql+psycopg://...tu URL de Neon del paso 1..."

cors_origin = "*"                                # se afina en el paso 5
```

Primer arranque en dos fases (los servicios de Cloud Run no pueden crearse
apuntando a imágenes que aún no existen):

```bash
terraform init

# Fase A: solo las APIs y el registro de imágenes
terraform apply -target=google_artifact_registry_repository.images

# Fase B: sube una primera versión de las imágenes a mano (única vez;
# --platform es importante en Macs Apple Silicon, Cloud Run es amd64)
gcloud auth configure-docker europe-southwest1-docker.pkg.dev
REPO=europe-southwest1-docker.pkg.dev/TU_PROJECT_ID/training-tracker
docker build ../../backend  --platform linux/amd64 --target production -t $REPO/api:bootstrap
docker build ../../frontend --platform linux/amd64 --target production -t $REPO/front:bootstrap
docker push $REPO/api:bootstrap && docker push $REPO/front:bootstrap
```

Apunta las imágenes bootstrap en `terraform.tfvars`:

```hcl
api_image   = "europe-southwest1-docker.pkg.dev/TU_PROJECT_ID/training-tracker/api:bootstrap"
front_image = "europe-southwest1-docker.pkg.dev/TU_PROJECT_ID/training-tracker/front:bootstrap"
```

Y el apply completo:

```bash
terraform apply     # revisa el plan y confirma con "yes"
```

Al terminar imprime los **outputs**: `api_url`, `front_url`,
`workload_identity_provider` y `deploy_service_account`. Los usarás ahora.

## 5. Cierra el círculo de URLs (2 min)

En `terraform.tfvars`, sustituye el CORS provisional por la URL real del front:

```hcl
cors_origin = "https://training-tracker-front-XXXX.a.run.app"   # el output front_url
```

```bash
terraform apply
```

## 6. Secrets de GitHub y primer despliegue real (5 min)

En GitHub → tu repo → *Settings → Secrets and variables → Actions →
New repository secret*, crea estos 5:

| Secret | Valor |
|---|---|
| `GCP_PROJECT_ID` | tu Project ID |
| `GCP_REGION` | `europe-southwest1` |
| `GCP_WIF_PROVIDER` | output `workload_identity_provider` de Terraform |
| `GCP_DEPLOY_SA` | output `deploy_service_account` de Terraform |
| `VITE_API_BASE_URL` | output `api_url` **+ `/api/v1`** (ej. `https://training-tracker-api-XXXX.a.run.app/api/v1`) |

Y lanza el primer despliegue de verdad:

```bash
git commit --allow-empty -m "Primer despliegue" && git push
```

En la pestaña *Actions* verás el workflow **Deploy**: tests → build de las dos
imágenes → deploy → smoke test contra `/health`. Cuando esté en verde, abre el
`front_url` en el móvil, crea tu cuenta y **"Añadir a pantalla de inicio"**.

## A partir de aquí

- **Desplegar cualquier cambio** = commit + push a `main`. Nada más: el
  workflow pasa los tests (si fallan, no se despliega), reconstruye, despliega
  y las migraciones de BD se aplican solas al arrancar la API.
- **Ver qué pasó en un deploy**: pestaña Actions del repo, o
  `gcloud run services describe training-tracker-api --region europe-southwest1`.
- **Rollback**: consola de Cloud Run → servicio → *Revisions* → dirigir el
  tráfico a la revisión anterior (cada revisión está etiquetada con el commit
  exacto que la generó).
- **Cambiar infraestructura** (memoria, regiones, secretos…): editar los `.tf`
  y `terraform apply`. Terraform no toca la versión desplegada del código
  (ignora el campo imagen a propósito, ver comentario en `cloud_run_api.tf`).

## Problemas típicos

| Síntoma | Causa |
|---|---|
| La primera visita del día tarda ~5 s | Cold start de Cloud Run (escala a cero) + Neon despertando. Normal en el tier gratuito. |
| El workflow falla en "auth" | Algún secret mal copiado, o el `github_repo` de terraform.tfvars no coincide exactamente con `usuario/repo`. |
| La web carga pero el login da error de red | `VITE_API_BASE_URL` mal (¿olvidaste el `/api/v1`?) o `cors_origin` no es exactamente la URL del front. |
| `exec format error` en los logs de Cloud Run | Imagen construida en Apple Silicon sin `--platform linux/amd64` (solo aplica a los push manuales del paso 4). |
| Las notificaciones no suenan en el móvil | Hay que abrir la PWA instalada (no la pestaña del navegador) y conceder el permiso en Ajustes. |

Antes de compartir la URL, repasa el checklist final de [SECURITY.md](SECURITY.md).
