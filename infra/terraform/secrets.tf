# =============================================================================
# Secret Manager: la API necesita DATABASE_URL, pero NO queremos que ese
# connection string (con la contraseña dentro) viva como variable de entorno
# en texto plano en la definición del servicio Cloud Run —cualquiera con
# permiso de "lector" en el proyecto podría verla en la consola. Secret
# Manager la guarda cifrada y Cloud Run la monta como si fuera una env var,
# pero solo la service account autorizada puede leerla (ver iam.tf).
# =============================================================================

locals {
  # Construye el connection string según el modo elegido:
  #  - Cloud SQL: conexión por socket Unix vía el proxy integrado de Cloud Run
  #    (no hay host/puerto de red, es un fichero especial montado en
  #    /cloudsql/<connection_name>, ver cloud_run_api.tf).
  #  - Externo (Neon/Supabase): la URL que te da el proveedor tal cual.
  database_url = var.use_cloud_sql ? (
    "postgresql+psycopg://${var.db_user}:${random_password.db_password[0].result}@/${var.db_name}?host=/cloudsql/${google_sql_database_instance.main[0].connection_name}"
  ) : var.external_database_url
}

resource "google_secret_manager_secret" "database_url" {
  project   = var.project_id
  secret_id = "${var.app_name}-database-url"

  replication {
    auto {} # deja que Google elija dónde replicar el secreto; no necesitamos control fino de región para un secreto de este tamaño
  }

  depends_on = [google_project_service.apis]
}

# Cada `apply` en el que cambie `local.database_url` (ej. rotas la contraseña)
# crea una NUEVA versión del secreto; Secret Manager conserva el histórico de
# versiones automáticamente, no hace falta gestionarlo a mano.
resource "google_secret_manager_secret_version" "database_url" {
  secret      = google_secret_manager_secret.database_url.id
  secret_data = local.database_url
}

# -----------------------------------------------------------------------------
# SECRET_KEY: la clave con la que la API firma los JWT de login. Quien la
# conozca puede fabricar tokens válidos para cualquier usuario, así que va a
# Secret Manager igual que DATABASE_URL. La genera Terraform una vez
# (random_password) y queda guardada en el state — otro motivo para tratar el
# state como sensible (ver README).
# -----------------------------------------------------------------------------
resource "random_password" "jwt_secret" {
  length  = 64
  special = false # solo alfanumérico: evita problemas de escapado y es igual de fuerte a esta longitud
}

resource "google_secret_manager_secret" "jwt_secret" {
  project   = var.project_id
  secret_id = "${var.app_name}-jwt-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "jwt_secret" {
  secret      = google_secret_manager_secret.jwt_secret.id
  secret_data = random_password.jwt_secret.result
}
