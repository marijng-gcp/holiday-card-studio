output "cloud_run_url" {
  description = "Deployed Cloud Run service URL."
  value       = google_cloud_run_v2_service.app.uri
}

output "service_account_email" {
  description = "Service account email running the ADK application."
  value       = google_service_account.agent_sa.email
}
