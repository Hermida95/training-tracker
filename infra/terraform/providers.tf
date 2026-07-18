# El "provider" es el plugin que traduce los recursos de este repo (google_*)
# en llamadas reales a la API de Google Cloud. `project` y `region` aquí son
# los valores por defecto para todos los recursos que no los especifiquen
# explícitamente.
provider "google" {
  project = var.project_id
  region  = var.region
}
