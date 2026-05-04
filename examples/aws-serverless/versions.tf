terraform {
  required_version = ">= 1.11.0, < 2.0.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.67.0"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.region
  default_tags {
    tags = {
      owner       = var.owner
      environment = var.environment
      project     = "tofu-release-kit"
    }
  }
}
