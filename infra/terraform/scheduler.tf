# =============================================================================
# Cloud Scheduler: los 3 recordatorios diarios por Telegram (rutina de
# mañana, comida, sesión de gym/running). Se prefiere esto a un cron de
# GitHub Actions (como el plan semanal, ver app/automation/weekly_plan.py)
# porque GitHub solo garantiza que un `schedule` se dispare "en algún
# momento" tras la hora pedida — en repos con poco tráfico eso puede tardar
# HORAS (ver el comentario largo en weekly_plan.py) — mientras que para un
# recordatorio de "son las 07:00" la hora exacta sí importa. Cloud Scheduler
# sí ofrece esa precisión, y sin coste: el free tier del proyecto son 3 jobs
# gratis, justo los que se crean aquí.
# =============================================================================

locals {
  # Los tres crons pegan al mismo servicio, solo cambia el path y el secreto
  # va igual en los tres: se define una vez y se reutiliza.
  scheduler_headers = {
    "Content-Type"       = "application/json"
    "X-Scheduler-Secret" = random_password.scheduler_shared_secret.result
  }
}

resource "google_cloud_scheduler_job" "notify_morning" {
  project     = var.project_id
  region      = var.region
  name        = "${var.app_name}-notify-morning"
  description = "Recordatorio diario de la rutina de mañana (Telegram)."
  schedule    = var.telegram_morning_cron
  time_zone   = var.app_timezone

  http_target {
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/internal/notify/morning"
    http_method = "POST"
    headers     = local.scheduler_headers
    body        = base64encode("{}")
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "notify_meal" {
  project     = var.project_id
  region      = var.region
  name        = "${var.app_name}-notify-meal"
  description = "Recordatorio diario de la comida principal (Telegram)."
  schedule    = var.telegram_meal_cron
  time_zone   = var.app_timezone

  http_target {
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/internal/notify/meal"
    http_method = "POST"
    headers     = local.scheduler_headers
    body        = base64encode("{}")
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_scheduler_job" "notify_training" {
  project     = var.project_id
  region      = var.region
  name        = "${var.app_name}-notify-training"
  description = "Recordatorio diario de la sesión de gym/running que toca (Telegram)."
  schedule    = var.telegram_training_cron
  time_zone   = var.app_timezone

  http_target {
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/internal/notify/training"
    http_method = "POST"
    headers     = local.scheduler_headers
    body        = base64encode("{}")
  }

  depends_on = [google_project_service.apis]
}
