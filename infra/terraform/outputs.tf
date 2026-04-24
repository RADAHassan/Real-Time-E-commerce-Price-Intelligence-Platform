output "bigtable_instance_id" {
  description = "Bigtable instance name"
  value       = google_bigtable_instance.main.name
}

output "gcs_bucket_name" {
  description = "GCS bucket for JSONL data"
  value       = google_storage_bucket.data.name
}

output "bigquery_raw_dataset" {
  value = google_bigquery_dataset.raw.dataset_id
}

output "bigquery_marts_dataset" {
  value = google_bigquery_dataset.marts.dataset_id
}

output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry_repo}"
}

output "service_account_email" {
  value = google_service_account.platform.email
}

output "api_url" {
  description = "Cloud Run URL for the FastAPI service"
  value       = length(google_cloud_run_v2_service.api) > 0 ? google_cloud_run_v2_service.api[0].uri : "not deployed"
}

output "frontend_url" {
  description = "Cloud Run URL for the React frontend"
  value       = length(google_cloud_run_v2_service.frontend) > 0 ? google_cloud_run_v2_service.frontend[0].uri : "not deployed"
}
