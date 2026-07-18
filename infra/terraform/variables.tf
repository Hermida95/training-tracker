# =============================================================================
# Variables de entrada. Se rellenan en terraform.tfvars (copia
# terraform.tfvars.example) o con -var en la CLI. Ninguna tiene un secreto de
# verdad dentro: las contraseñas se generan solas (ver secrets.tf) o se pasan
# por variable de entorno TF_VAR_... para no dejarlas escritas en un fichero.
# =============================================================================

variable "project_id" {
  description = "ID del proyecto de GCP (no el nombre bonito, el id: ej. 'training-tracker-123456')."
  type        = string
}

variable "region" {
  description = "Región de GCP donde vive todo. Cloud Run y Cloud SQL deben estar en la misma región para conectarse por red interna sin coste ni latencia extra."
  type        = string
  default     = "europe-southwest1" # Madrid
}

variable "app_name" {
  description = "Prefijo usado para nombrar todos los recursos (servicios, repos, secretos...). Cámbialo si despliegas varios entornos en el mismo proyecto."
  type        = string
  default     = "training-tracker"
}

variable "api_image" {
  description = "Imagen Docker del backend, con tag. Se actualiza en cada despliegue (ver README → CI/CD). Ejemplo: europe-southwest1-docker.pkg.dev/PROJECT/training-tracker/api:latest"
  type        = string
}

variable "front_image" {
  description = "Imagen Docker del frontend, con tag. Igual que api_image pero para el servicio de React."
  type        = string
}

# -----------------------------------------------------------------------------
# Base de datos: por defecto este Terraform crea una instancia de Cloud SQL
# (Postgres gestionado por Google). Si prefieres NO pagar por Cloud SQL y usar
# un Postgres gratuito externo (Neon o Supabase, ver README → "Alternativa
# gratuita"), pon use_cloud_sql = false y rellena external_database_url con
# la connection string que te da ese proveedor: Terraform entonces se salta
# por completo la creación de Cloud SQL y solo mete esa URL en Secret Manager.
# -----------------------------------------------------------------------------

variable "use_cloud_sql" {
  description = "true = Terraform crea y gestiona una instancia de Cloud SQL. false = usas un Postgres externo (Neon/Supabase) y solo pasas su URL."
  type        = bool
  default     = true
}

variable "external_database_url" {
  description = "Solo si use_cloud_sql = false: connection string completa de Neon/Supabase (postgresql+psycopg://user:pass@host/db?sslmode=require)."
  type        = string
  default     = ""
  sensitive   = true
}

variable "cloud_sql_tier" {
  description = "Tamaño de la instancia de Cloud SQL. db-f1-micro es el más pequeño/barato, de sobra para uso personal."
  type        = string
  default     = "db-f1-micro"
}

variable "db_name" {
  description = "Nombre de la base de datos dentro del motor Postgres."
  type        = string
  default     = "training_tracker"
}

variable "db_user" {
  description = "Usuario de la base de datos que usará la API."
  type        = string
  default     = "trainer"
}

variable "cors_origin" {
  description = "URL del frontend, para configurar CORS en la API. Se rellena en un segundo 'apply' una vez Cloud Run asigna la URL del front (ver README, es un problema de huevo-y-gallina típico de Cloud Run)."
  type        = string
  default     = "*"
}

variable "app_timezone" {
  description = "Zona horaria fija para toda la lógica de fechas/streaks/alarma."
  type        = string
  default     = "Europe/Madrid"
}
