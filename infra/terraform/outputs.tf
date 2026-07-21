# Lo que Terraform imprime al final de un `apply` (y lo que puedes volver a
# consultar luego con `terraform output`). Útil para no tener que ir a buscar
# las URLs a mano en la consola de Cloud Run cada vez.

output "api_url" {
  description = "URL pública de la API (usar como VITE_API_BASE_URL + /api/v1 al construir el front)."
  value       = google_cloud_run_v2_service.api.uri
}

output "front_url" {
  description = "URL pública de la PWA. Es la que compartes / instalas en el móvil."
  value       = google_cloud_run_v2_service.front.uri
}

output "artifact_registry_repo" {
  description = "Ruta del repositorio Docker, para el 'docker push' del CI/CD."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}"
}

output "cloud_sql_connection_name" {
  description = "Connection name de la instancia (PROJECT:REGION:INSTANCE). Vacío si use_cloud_sql = false."
  value       = var.use_cloud_sql ? google_sql_database_instance.main[0].connection_name : null
}

# --- Los dos valores que hay que copiar a los secrets de GitHub (ver DEPLOY.md) ---

output "workload_identity_provider" {
  description = "Pégalo en el secret GCP_WIF_PROVIDER de GitHub: identifica el provider OIDC contra el que se autentica el workflow."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deploy_service_account" {
  description = "Pégalo en el secret GCP_DEPLOY_SA de GitHub: la service account que impersona el workflow para desplegar."
  value       = google_service_account.deployer.email
}
