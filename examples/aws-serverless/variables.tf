variable "region" {
  type    = string
  default = "us-east-2"
}

variable "owner" {
  type = string
  validation {
    condition     = length(trimspace(var.owner)) > 0
    error_message = "An accountable owner is required."
  }
}

variable "environment" {
  type    = string
  default = "sandbox"
  validation {
    condition     = contains(["sandbox", "staging"], var.environment)
    error_message = "This disposable example supports sandbox or staging only."
  }
}

variable "application_revision" {
  type = string
  validation {
    condition     = can(regex("^[0-9a-f]{40}$", var.application_revision))
    error_message = "Use the full application Git commit SHA."
  }
}

variable "package_path" {
  type    = string
  default = ".artifacts/function.zip"
}
