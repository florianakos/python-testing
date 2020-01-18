variable "region" {
  type = string
  default = "eu-central-1" # Frankfurt
}

variable "bucket_name" {
  type = string
  default = "cloud-job-results-bucket"
}

variable "queue_name" {
  type = string
  default = "cloud-job-results-queue"
}