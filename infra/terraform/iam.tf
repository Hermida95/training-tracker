# =============================================================================
# Permisos. Cada bloque de abajo es una pregunta de "¿quién puede hacer qué
# sobre qué recurso?" — el equivalente Terraform de ir a la pestaña IAM de un
# recurso en la consola y añadir un miembro con un rol.
# =============================================================================

# 1) La service account de la API puede LEER (no escribir) el secreto con el
#    connection string de la base de datos. Sin esto, Cloud Run arrancaría el
#    contenedor pero fallaría al intentar montar el secreto como env var.
resource "google_secret_manager_secret_iam_member" "api_reads_db_url" {
  secret_id = google_secret_manager_secret.database_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.api_runtime.email}"
}

# 2) Si usamos Cloud SQL, la service account necesita permiso para abrir el
#    túnel del proxy integrado hacia la instancia (sin esto, el volumen
#    cloud_sql_instance de cloud_run_api.tf se monta pero las conexiones
#    fallan con un error de permisos).
resource "google_project_iam_member" "api_cloudsql_client" {
  count = var.use_cloud_sql ? 1 : 0

  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.api_runtime.email}"
}

# 3) Hace público el servicio de API: cualquiera con la URL puede llamar a la
#    REST API sin autenticarse. Es lo esperado para una API que consume tu
#    propio frontend desde el navegador del móvil (no hay backend-to-backend
#    de por medio que pudiera usar autenticación de servicio a servicio).
#    Si en el futuro quieres cerrarlo, quita este recurso y usa Identity-Aware
#    Proxy o un API Gateway delante.
resource "google_cloud_run_v2_service_iam_member" "api_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# 4) Igual que el anterior pero para el frontend: la web estática debe ser
#    accesible por cualquiera, es una PWA pública.
resource "google_cloud_run_v2_service_iam_member" "front_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.front.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
