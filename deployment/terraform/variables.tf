variable "project_id" {
  description = "Target GCP project ID (e.g., l200dy5-sandbox-68969)."
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run and Artifact Registry."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name."
  type        = string
  default     = "holiday-card-studio"
}

variable "image_uri" {
  description = "Container image URI in Artifact Registry."
  type        = string
}

variable "ingress" {
  description = "Cloud Run ingress policy. Use INGRESS_TRAFFIC_INTERNAL_ONLY in L200 sandbox, INGRESS_TRAFFIC_ALL in public prod."
  type        = string
  default     = "INGRESS_TRAFFIC_INTERNAL_ONLY"
}

variable "fast_model" {
  description = "Fast Gemini model ID for copywriting, critique, and compaction."
  type        = string
  default     = "gemini-2.5-flash"
}

variable "pro_model" {
  description = "Pro Gemini model ID for ArtDirector reasoning."
  type        = string
  default     = "gemini-2.5-pro"
}

variable "image_model" {
  description = "Vertex AI image generation model ID."
  type        = string
  default     = "imagen-3.0-generate-002"
}
