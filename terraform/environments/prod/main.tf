# Production environment Terraform configuration
terraform {
  backend "s3" {
    bucket = "dummy-infra-terraform-state"
    # BUG: Same state key as dev - environments will overwrite each other
    key    = "dummy-infra/terraform.tfstate"
    region = "us-east-1"
  }
}

module "main" {
  source = "../../"

  environment = "prod"
  vpc_cidr    = "10.0.0.0/8"
}
