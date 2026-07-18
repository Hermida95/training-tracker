# Repositorio Docker privado donde `docker push` sube las imágenes de api y
# front antes de que Cloud Run las despliegue. Sin esto no hay dónde alojar
# las imágenes dentro de GCP (podrías usar Docker Hub, pero Artifact Registry
# evita salir de la red de Google y es lo que espera el resto de este Terraform).
resource "google_artifact_registry_repository" "images" {
  project  = var.project_id
  location = var.region

  repository_id = var.app_name
  format        = "DOCKER"
  description   = "Imágenes Docker de ${var.app_name} (api + front)"

  depends_on = [google_project_service.apis]
}
