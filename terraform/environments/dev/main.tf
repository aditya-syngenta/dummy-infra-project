# Dev environment Terraform configuration
# BUG: Dev and prod use same state file path
terraform {
  backend "s3" {
    bucket = "dummy-infra-terraform-state"
    # BUG: Same key as prod - will overwrite prod state!
    key    = "dummy-infra/terraform.tfstate"
    region = "us-east-1"
    # BUG: No state locking (dynamodb_table not set)
  }
}

module "main" {
  source = "../../"

  # BUG: Dev environment uses production-sized resources
  environment = "dev"
  # BUG: Wrong CIDR for dev that conflicts with prod
  vpc_cidr    = "10.0.0.0/8"
}
