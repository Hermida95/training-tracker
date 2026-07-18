# Un proyecto de GCP nuevo tiene casi todas las APIs desactivadas (por coste y
# seguridad). `google_project_service` es el equivalente Terraform de ir a la
# consola y darle a "Habilitar API" en cada una. Si un recurso más abajo usa
# una API no habilitada aquí, el apply falla con un error bastante claro
# pidiéndote que la actives — así que las listamos todas por adelantado.
locals {
  required_apis = [
    "run.googleapis.com",                 # Cloud Run: para desplegar los contenedores de api y front
    "artifactregistry.googleapis.com",    # Artifact Registry: dónde viven las imágenes Docker
    "secretmanager.googleapis.com",       # Secret Manager: guarda DATABASE_URL sin exponerla en variables de entorno planas
    "sqladmin.googleapis.com",            # Cloud SQL Admin: solo hace falta si use_cloud_sql = true, pero habilitarla de más no molesta
    "iam.googleapis.com",                 # IAM: para crear la service account dedicada de Cloud Run
    "cloudresourcemanager.googleapis.com" # Requisito interno de Terraform para leer metadatos del proyecto
  ]
}

resource "google_project_service" "apis" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  # Si algún día haces `terraform destroy`, por defecto también desactivaría
  # las APIs. Eso puede romper OTRAS cosas que uses en el mismo proyecto GCP
  # que no gestiona este Terraform, así que lo desactivamos: destruir esta
  # infra no debe "apagar" el proyecto entero.
  disable_on_destroy = false
}
