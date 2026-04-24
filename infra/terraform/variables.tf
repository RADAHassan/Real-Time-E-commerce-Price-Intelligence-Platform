variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone (for zonal resources)"
  type        = string
  default     = "us-central1-a"
}

variable "bigtable_instance_id" {
  description = "Bigtable instance name"
  type        = string
  default     = "price-intelligence"
}

variable "bigquery_dataset_id" {
  description = "Root BigQuery dataset name (suffixes _raw / _staging / _marts are appended)"
  type        = string
  default     = "price_intelligence"
}

variable "gcs_bucket_name" {
  description = "GCS bucket for JSONL staging files"
  type        = string
  default     = ""   # defaults to '<project_id>-price-intelligence-data'
}

variable "artifact_registry_repo" {
  description = "Artifact Registry repository name for Docker images"
  type        = string
  default     = "price-intelligence"
}

variable "api_image" {
  description = "Full Docker image URI for the FastAPI service"
  type        = string
  default     = ""   # e.g. ghcr.io/radahassan/price-intelligence-api:latest
}

variable "frontend_image" {
  description = "Full Docker image URI for the React/Nginx frontend"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment label"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}
