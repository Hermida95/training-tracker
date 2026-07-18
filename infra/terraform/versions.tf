# Fija las versiones de Terraform y del provider de Google para que "terraform
# apply" se comporte igual hoy que dentro de 6 meses, aunque salgan versiones
# nuevas del provider con cambios incompatibles. Es la práctica estándar de
# cualquier proyecto Terraform en equipo.
terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.10"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Dónde vive el "state" (el archivo que registra qué recursos existen ya
  # y con qué configuración). Por defecto Terraform lo guarda en un fichero
  # local (terraform.tfstate) — válido para aprender y para un proyecto
  # personal como este. Si en el futuro trabajas en equipo, descomenta este
  # bloque y usa un bucket de Cloud Storage como backend remoto, para que
  # el state no viva solo en tu portátil y dos personas no lo pisen a la vez.
  #
  # backend "gcs" {
  #   bucket = "TU_BUCKET_DE_STATE"
  #   prefix = "training-tracker"
  # }
}
