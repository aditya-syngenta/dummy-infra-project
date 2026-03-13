# BUG: No required_providers block with version constraints
# BUG: No backend configuration - state stored locally
# BUG: No remote state locking

terraform {
  # BUG: Terraform version constraint too broad
  required_version = ">= 0.12"
}

provider "aws" {
  # BUG: Region hardcoded instead of using variable
  region = "us-east-1"

  # BUG: Access keys hardcoded in provider (should use IAM roles or env vars)
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}

# BUG: No workspace-based environment separation
locals {
  project_name = "dummy-infra"
  environment  = "production"  # BUG: Hardcoded environment
  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    # BUG: Missing Owner and CostCenter tags
  }
}

# VPC Module
module "vpc" {
  source = "./modules/vpc"

  project_name = local.project_name
  environment  = local.environment
  # BUG: CIDR block too large for production use
  vpc_cidr     = "10.0.0.0/8"
  tags         = local.common_tags
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  project_name = local.project_name
  environment  = local.environment
  vpc_id       = module.vpc.vpc_id
  # BUG: Using public subnets for ECS tasks instead of private
  subnet_ids   = module.vpc.public_subnet_ids
  tags         = local.common_tags
}

# RDS Module
module "rds" {
  source = "./modules/rds"

  project_name    = local.project_name
  environment     = local.environment
  vpc_id          = module.vpc.vpc_id
  # BUG: Database placed in public subnet - should be private
  subnet_ids      = module.vpc.public_subnet_ids
  # BUG: Hardcoded DB password
  db_password     = "Passw0rd123!"
  tags            = local.common_tags
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  project_name = local.project_name
  environment  = local.environment
  tags         = local.common_tags
}

# ElastiCache Module
module "elasticache" {
  source = "./modules/elasticache"

  project_name = local.project_name
  environment  = local.environment
  vpc_id       = module.vpc.vpc_id
  # BUG: Cache in public subnet
  subnet_ids   = module.vpc.public_subnet_ids
  tags         = local.common_tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  project_name = local.project_name
  environment  = local.environment
}

# BUG: Outputs sensitive values in plaintext
output "db_password" {
  value = module.rds.db_password
}

output "redis_endpoint" {
  value = module.elasticache.endpoint
}
