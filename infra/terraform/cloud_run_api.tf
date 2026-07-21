# =============================================================================
# Cloud Run: el backend FastAPI. `google_cloud_run_v2_service` es la versión
# moderna del recurso (hay una v1 "google_cloud_run_service" más antigua,
# evítala en proyectos nuevos). Cloud Run = "dame un contenedor Docker y una
# imagen, yo me encargo de levantar instancias según el tráfico, HTTPS,
# balanceo y bajar a 0 instancias (0 coste) cuando nadie lo usa".
# =============================================================================

resource "google_cloud_run_v2_service" "api" {
  project  = var.project_id
  name     = "${var.app_name}-api"
  location = var.region

  # ALL = acepta tráfico de cualquier origen (internet). La alternativa
  # INGRESS_TRAFFIC_INTERNAL_ONLY serviría si esta API solo la llamara otro
  # servicio de Google Cloud, pero aquí la llama el navegador del usuario.
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    # Identidad con permisos mínimos definida en service_accounts.tf, en vez
    # de la cuenta por defecto de Compute Engine (ver comentario allí).
    service_account = google_service_account.api_runtime.email

    scaling {
      min_instance_count = 0 # a 0 tráfico, 0 instancias, 0 coste (con "cold start" en la siguiente petición)
      max_instance_count = 3 # techo de instancias en paralelo; de sobra y evita una factura sorpresa si algo hace un bucle de peticiones
    }

    containers {
      image = var.api_image # ej. europe-southwest1-docker.pkg.dev/PROJECT/training-tracker/api:latest

      ports {
        container_port = 8080 # debe coincidir con el ENV PORT=8080 del Dockerfile de backend
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }

      # --- Variables de entorno "normales": valores no sensibles ---
      env {
        name  = "ENVIRONMENT"
        value = "production"
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origin
      }
      env {
        name  = "APP_TIMEZONE"
        value = var.app_timezone
      }

      # --- Variable de entorno secreta: Cloud Run la resuelve leyendo
      # Secret Manager en el momento de arrancar el contenedor, la app nunca
      # ve el secret_id, solo recibe DATABASE_URL como si fuera una env var
      # normal (`os.environ["DATABASE_URL"]` en Python no distingue el origen). ---
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.database_url.secret_id
            version = "latest"
          }
        }
      }

      # SECRET_KEY firma los JWT del login (ver app/core/security.py). Mismo
      # mecanismo que DATABASE_URL: la app la recibe como env var normal.
      env {
        name = "SECRET_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.jwt_secret.secret_id
            version = "latest"
          }
        }
      }

      # Solo si usamos Cloud SQL: monta el volumen especial /cloudsql (ver
      # bloque `volumes` más abajo) para que psycopg pueda abrir el socket
      # Unix que espera la connection string de secrets.tf.
      dynamic "volume_mounts" {
        for_each = var.use_cloud_sql ? [1] : []
        content {
          name       = "cloudsql"
          mount_path = "/cloudsql"
        }
      }

      # Cloud Run no manda tráfico real a una instancia nueva hasta que el
      # startup probe pasa: evita que un cold start reciba peticiones de
      # usuario mientras Alembic todavía está aplicando migraciones.
      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 5
        period_seconds        = 5
        failure_threshold     = 6
        timeout_seconds       = 3
      }
    }

    # El "volumen" cloud_sql_instance es la forma que tiene Cloud Run de traer
    # integrado el Cloud SQL Auth Proxy, sin tener que correrlo tú mismo como
    # sidecar: Google gestiona el túnel cifrado hacia la instancia por debajo.
    dynamic "volumes" {
      for_each = var.use_cloud_sql ? [1] : []
      content {
        name = "cloudsql"
        cloud_sql_instance {
          instances = [google_sql_database_instance.main[0].connection_name]
        }
      }
    }
  }

  # Terraform no adivina que necesita las APIs habilitadas o el secreto
  # relleno antes de crear el servicio; se lo decimos explícitamente para que
  # el orden de creación sea siempre el correcto en un `apply` desde cero.
  # El CI/CD actualiza la imagen en cada push a main (`gcloud run deploy`);
  # sin este ignore_changes, un `terraform apply` posterior la revertiría.
  # Terraform gestiona la infraestructura; el pipeline, la versión del código.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.database_url,
    google_secret_manager_secret_version.jwt_secret,
  ]
}
