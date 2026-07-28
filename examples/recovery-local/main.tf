terraform {
  required_version = ">= 1.6.0, < 2.0.0"
}

variable "revision" {
  type    = string
  default = "first"
}

resource "terraform_data" "release" {
  input = var.revision
}

output "revision" {
  value = terraform_data.release.output
}
