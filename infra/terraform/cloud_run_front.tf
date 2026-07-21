# Cloud Run del frontend: nginx sirviendo el bundle estático de React. No
# necesita base de datos ni secretos — la URL de la API ya quedó "horneada"
# dentro del JS en build-time (ver frontend/Dockerfile, ARG VITE_API_BASE_URL),
# así que este servicio es mucho más simple que el de la API.
resource "google_cloud_run_v2_service" "front" {
  project  = var.project_id
  name     = "${var.app_name}-front"
  location = var.region

  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    # Identidad mínima sin roles (ver service_accounts.tf).
    service_account = google_service_account.front_runtime.email

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    containers {
      image = var.front_image

      ports {
        container_port = 8080 # coincide con el ENV PORT=8080 / nginx.conf del frontend
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi" # mínimo que acepta Cloud Run con la config de CPU por defecto (con 256Mi el apply falla)
        }
      }

      startup_probe {
        http_get {
          path = "/"
        }
        initial_delay_seconds = 2
        period_seconds        = 3
        failure_threshold     = 5
      }
    }
  }

  # El CI/CD (GitHub Actions) actualiza la imagen con `gcloud run deploy` en
  # cada push a main. Sin este ignore_changes, el siguiente `terraform apply`
  # vería "la imagen del servicio no coincide con var.front_image" y la
  # revertiría a una versión vieja. Terraform es dueño de la infraestructura;
  # el pipeline es dueño de QUÉ versión del código corre en ella.
  lifecycle {
    ignore_changes = [template[0].containers[0].image]
  }

  depends_on = [google_project_service.apis]
}
