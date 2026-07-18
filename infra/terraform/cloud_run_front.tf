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
          memory = "256Mi" # nginx sirviendo estáticos consume muy poco
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

  depends_on = [google_project_service.apis]
}
