# =============================================================================
# Cloud SQL: solo se crea si use_cloud_sql = true (ver variables.tf). El
# patrón `count = var.use_cloud_sql ? 1 : 0` es la forma que tiene Terraform
# de decir "0 o 1 copias de este recurso": con count=0 el recurso simplemente
# no existe, como si el bloque no estuviera. Por eso todas las referencias a
# estos recursos en otros ficheros usan `[0]` (el primer y único elemento) y
# van envueltas en `try(..., null)` cuando use_cloud_sql puede ser false.
# =============================================================================

# Contraseña de base de datos generada al azar por Terraform, no escrita a
# mano en ningún fichero. `random_password` crea el valor una vez y lo deja
# fijo en el state (no cambia en cada apply, salvo que borres el recurso).
resource "random_password" "db_password" {
  count   = var.use_cloud_sql ? 1 : 0
  length  = 24
  special = false # evita caracteres que compliquen el connection string (@, /, ?, etc.)
}

# La instancia en sí: el servidor Postgres gestionado por Google (parches,
# backups y HA los lleva Google, tú solo pagas por el tamaño de la máquina).
resource "google_sql_database_instance" "main" {
  count = var.use_cloud_sql ? 1 : 0

  project          = var.project_id
  name             = "${var.app_name}-db"
  region           = var.region
  database_version = "POSTGRES_16"

  # Evita que un `terraform destroy` accidental borre la base de datos con
  # todos tus entrenos. Para borrarla de verdad hay que quitar esta línea (o
  # ponerla a false) en un commit aparte, a propósito.
  deletion_protection = true

  settings {
    tier = var.cloud_sql_tier # db-f1-micro: 1 vCPU compartida, ~0.6GB RAM. Suficiente para uso personal.

    # Sin IP pública: Cloud Run se conecta por el conector interno de Cloud
    # SQL (ver cloud_run_api.tf → volumes.cloud_sql_instance), así la base de
    # datos no queda expuesta a internet en ningún momento.
    ip_configuration {
      ipv4_enabled = false
    }

    backup_configuration {
      enabled    = true
      start_time = "03:00" # de madrugada en hora UTC, cuando nadie está entrenando
    }
  }
}

resource "google_sql_database" "main" {
  count = var.use_cloud_sql ? 1 : 0

  project  = var.project_id
  name     = var.db_name
  instance = google_sql_database_instance.main[0].name
}

resource "google_sql_user" "main" {
  count = var.use_cloud_sql ? 1 : 0

  project  = var.project_id
  name     = var.db_user
  instance = google_sql_database_instance.main[0].name
  password = random_password.db_password[0].result
}
