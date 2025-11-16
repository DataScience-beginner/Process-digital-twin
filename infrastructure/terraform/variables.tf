variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "refinerydt"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Refinery Digital Twin"
    ManagedBy   = "Terraform"
    Environment = "Development"
  }
}
