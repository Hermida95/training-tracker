# =============================================================================
# CI/CD: permite que GitHub Actions despliegue en Cloud Run SIN guardar ninguna
# clave de Google en GitHub.
#
# ¿Cómo? Workload Identity Federation (WIF). La idea en una frase: en vez de
# darle a GitHub una contraseña de GCP, le decimos a GCP "confía en los tokens
# que firma GitHub para este repositorio concreto". En cada ejecución del
# workflow, GitHub emite un token OIDC (un JWT firmado por GitHub que dice
# "soy el repo X, rama Y"), GCP lo verifica contra la clave pública de GitHub
# y lo cambia por credenciales temporales de la service account de deploy.
# No hay ningún secreto de larga duración que se pueda filtrar.
# =============================================================================

# -----------------------------------------------------------------------------
# 1) El "pool": un contenedor lógico de identidades externas. Piensa en él
#    como "el grupo de identidades que vienen de fuera de Google". Puedes tener
#    varios providers dentro (GitHub, GitLab...); aquí solo GitHub.
# -----------------------------------------------------------------------------
resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions"

  depends_on = [google_project_service.apis]
}

# -----------------------------------------------------------------------------
# 2) El "provider": QUIÉN emite los tokens y CÓMO interpretarlos.
#    - issuer_uri: la URL oficial de OIDC de GitHub Actions. GCP descarga de
#      ahí las claves públicas con las que verificar la firma de los tokens.
#    - attribute_mapping: traduce los campos ("claims") del token de GitHub a
#      atributos que GCP entiende. `assertion.repository` es el claim que
#      GitHub mete con el nombre "usuario/repo" del workflow que pide el token.
#    - attribute_condition: EL CANDADO. Sin esto, cualquier repo de GitHub del
#      mundo podría intentar autenticarse contra tu pool. Con la condición,
#      solo los tokens cuyo claim repository sea exactamente tu repo pasan.
# -----------------------------------------------------------------------------
resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub OIDC"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == \"${var.github_repo}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# -----------------------------------------------------------------------------
# 3) La service account que "es" el deploy: los permisos que tenga esta cuenta
#    son exactamente lo que el workflow de GitHub puede hacer en GCP. Ni más.
# -----------------------------------------------------------------------------
resource "google_service_account" "deployer" {
  project      = var.project_id
  account_id   = "${var.app_name}-deployer"
  display_name = "Deploy desde GitHub Actions (${var.github_repo})"
}

# 4) El pegamento entre 2) y 3): los tokens del pool cuyo atributo repository
#    sea tu repo pueden "actuar como" (impersonar) la SA de deploy. Es el
#    binding workloadIdentityUser sobre la propia service account.
resource "google_service_account_iam_member" "github_impersonates_deployer" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo}"
}

# -----------------------------------------------------------------------------
# 5) Permisos mínimos de la SA de deploy:
#    - run.developer: crear nuevas revisiones de los servicios de Cloud Run
#      (desplegar). NO puede cambiar permisos IAM ni borrar servicios.
#    - artifactregistry.writer: hacer `docker push` de las imágenes, acotado
#      al repositorio de imágenes concreto (no a todo el proyecto).
#    - serviceAccountUser sobre las SAs de RUNTIME: Cloud Run exige que quien
#      despliega tenga permiso de "usar" la identidad con la que correrá el
#      servicio — evita que alguien con permiso de deploy escale privilegios
#      desplegando código que corra como una cuenta más poderosa.
# -----------------------------------------------------------------------------
resource "google_project_iam_member" "deployer_run" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_artifact_registry_repository_iam_member" "deployer_push" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.images.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_uses_api_runtime" {
  service_account_id = google_service_account.api_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "deployer_uses_front_runtime" {
  service_account_id = google_service_account.front_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}
