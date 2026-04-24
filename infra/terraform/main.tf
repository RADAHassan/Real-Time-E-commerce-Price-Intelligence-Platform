terraform {
  required_version = ">= 1.6"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  # Uncomment to store state in GCS (recommended for production)
  # backend "gcs" {
  #   bucket = "<your-tf-state-bucket>"
  #   prefix = "price-intelligence/state"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  bucket_name = var.gcs_bucket_name != "" ? var.gcs_bucket_name : "${var.project_id}-price-intelligence-data"
  labels      = { app = "price-intelligence", env = var.environment }
}

# ──────────────────────────────────────────────────────────────────────────────
# Enable required GCP APIs
# ──────────────────────────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "bigtable.googleapis.com",
    "bigtableadmin.googleapis.com",
    "bigquery.googleapis.com",
    "storage.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "composer.googleapis.com",
    "iam.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Bigtable
# ──────────────────────────────────────────────────────────────────────────────

resource "google_bigtable_instance" "main" {
  name         = var.bigtable_instance_id
  display_name = "Price Intelligence"
  labels       = local.labels

  cluster {
    cluster_id   = "${var.bigtable_instance_id}-c1"
    zone         = var.zone
    num_nodes    = 1              # scale up for production
    storage_type = "SSD"
  }

  depends_on = [google_project_service.apis]
}

resource "google_bigtable_table" "prices" {
  name          = "prices"
  instance_name = google_bigtable_instance.main.name

  column_family { family = "price_cf" }
  column_family { family = "metadata_cf" }
  column_family { family = "agg_cf" }
}

# ──────────────────────────────────────────────────────────────────────────────
# Google Cloud Storage — JSONL staging
# ──────────────────────────────────────────────────────────────────────────────

resource "google_storage_bucket" "data" {
  name          = local.bucket_name
  location      = var.region
  force_destroy = false
  labels        = local.labels

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition { age = 90 }
    action    { type = "Delete" }
  }
}

# ──────────────────────────────────────────────────────────────────────────────
# BigQuery datasets
# ──────────────────────────────────────────────────────────────────────────────

resource "google_bigquery_dataset" "raw" {
  dataset_id                 = "${var.bigquery_dataset_id}_raw"
  location                   = "US"
  description                = "Raw scraped price data loaded by Airflow"
  delete_contents_on_destroy = false
  labels                     = local.labels
  depends_on                 = [google_project_service.apis]
}

resource "google_bigquery_dataset" "staging" {
  dataset_id                 = "${var.bigquery_dataset_id}_staging"
  location                   = "US"
  description                = "dbt staging layer (views)"
  delete_contents_on_destroy = false
  labels                     = local.labels
  depends_on                 = [google_project_service.apis]
}

resource "google_bigquery_dataset" "marts" {
  dataset_id                 = "${var.bigquery_dataset_id}_marts"
  location                   = "US"
  description                = "dbt marts layer (tables consumed by API and dashboard)"
  delete_contents_on_destroy = false
  labels                     = local.labels
  depends_on                 = [google_project_service.apis]
}

# ──────────────────────────────────────────────────────────────────────────────
# Artifact Registry
# ──────────────────────────────────────────────────────────────────────────────

resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.artifact_registry_repo
  format        = "DOCKER"
  description   = "Docker images for Price Intelligence Platform"
  labels        = local.labels
  depends_on    = [google_project_service.apis]
}

# ──────────────────────────────────────────────────────────────────────────────
# IAM — service account for the platform
# ──────────────────────────────────────────────────────────────────────────────

resource "google_service_account" "platform" {
  account_id   = "price-intelligence-sa"
  display_name = "Price Intelligence Platform"
}

resource "google_project_iam_member" "roles" {
  for_each = toset([
    "roles/bigtable.user",
    "roles/bigquery.dataEditor",
    "roles/bigquery.jobUser",
    "roles/storage.objectAdmin",
    "roles/run.invoker",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.platform.email}"
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run — FastAPI (api)
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "api" {
  count    = var.api_image != "" ? 1 : 0
  name     = "price-intelligence-api"
  location = var.region
  labels   = local.labels

  template {
    service_account = google_service_account.platform.email

    containers {
      image = var.api_image
      ports { container_port = 8000 }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "BIGQUERY_DATASET"
        value = var.bigquery_dataset_id
      }
      env {
        name  = "USE_MOCK_DATA"
        value = "false"
      }

      resources {
        limits = { cpu = "1", memory = "512Mi" }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "api_public" {
  count    = var.api_image != "" ? 1 : 0
  location = google_cloud_run_v2_service.api[0].location
  name     = google_cloud_run_v2_service.api[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ──────────────────────────────────────────────────────────────────────────────
# Cloud Run — React/Nginx (frontend)
# ──────────────────────────────────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "frontend" {
  count    = var.frontend_image != "" ? 1 : 0
  name     = "price-intelligence-frontend"
  location = var.region
  labels   = local.labels

  template {
    containers {
      image = var.frontend_image
      ports { container_port = 80 }

      resources {
        limits = { cpu = "0.5", memory = "256Mi" }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  depends_on = [google_project_service.apis]
}

resource "google_cloud_run_v2_service_iam_member" "frontend_public" {
  count    = var.frontend_image != "" ? 1 : 0
  location = google_cloud_run_v2_service.frontend[0].location
  name     = google_cloud_run_v2_service.frontend[0].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
