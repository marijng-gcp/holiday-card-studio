terraform {
  required_version = ">= 1.6.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_service_account" "agent_sa" {
  account_id   = "holiday-card-agent-sa"
  display_name = "Holiday Card Studio Agent Service Account"
}

locals {
  agent_roles = [
    "roles/aiplatform.user",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
    "roles/secretmanager.secretAccessor",
    "roles/dlp.user",
  ]
}

resource "google_project_iam_member" "agent_sa_roles" {
  for_each = toset(local.agent_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_artifact_registry_repository" "repo" {
  location      = var.region
  repository_id = var.service_name
  format        = "DOCKER"
  description   = "Container images for Holiday Card Studio"
}

resource "google_secret_manager_secret" "theme_config" {
  secret_id = "holiday-card-theme-config"
  replication {
    auto {}
  }
}

resource "google_cloud_run_v2_service" "app" {
  name     = var.service_name
  location = var.region
  ingress  = var.ingress

  template {
    service_account = google_service_account.agent_sa.email

    containers {
      image = var.image_uri

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "true"
      }
      env {
        name  = "FAST_MODEL"
        value = var.fast_model
      }
      env {
        name  = "PRO_MODEL"
        value = var.pro_model
      }
      env {
        name  = "IMAGE_MODEL"
        value = var.image_model
      }
      env {
        name  = "ENABLE_CLOUD_TRACE"
        value = "true"
      }
      env {
        name  = "ENABLE_CLOUD_DLP"
        value = "true"
      }
      env {
        name  = "ENABLE_SECRET_MANAGER"
        value = "true"
      }
    }
  }

  depends_on = [google_project_iam_member.agent_sa_roles]
}
