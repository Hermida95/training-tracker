# Por defecto, si no le dices lo contrario, Cloud Run ejecuta tu contenedor
# con la service account "Compute Engine default", que tiene permisos de
# editor muy amplios sobre TODO el proyecto — un riesgo innecesario si algún
# día hay un bug de seguridad en la API. Creamos una identidad propia, mínima,
# solo para este servicio (principio de menor privilegio).
resource "google_service_account" "api_runtime" {
  project      = var.project_id
  account_id   = "${var.app_name}-api"
  display_name = "Runtime SA de ${var.app_name}-api (Cloud Run)"
}

# Misma idea para el frontend. nginx sirviendo estáticos no necesita NINGÚN
# permiso de GCP, así que esta cuenta no tiene ni un solo rol — su única
# función es NO ser la cuenta por defecto de Compute (que tiene demasiados).
resource "google_service_account" "front_runtime" {
  project      = var.project_id
  account_id   = "${var.app_name}-front"
  display_name = "Runtime SA de ${var.app_name}-front (Cloud Run)"
}
