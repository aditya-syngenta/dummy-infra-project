variable "project_name" {}
variable "environment" {}
variable "vpc_id" {}
variable "subnet_ids" {}
variable "db_password" {}
variable "tags" { default = {} }

# BUG: No DB subnet group - RDS may launch in wrong subnet
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet"
  subnet_ids = var.subnet_ids

  tags = var.tags
}

# BUG: Security group allows DB access from entire internet
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "RDS Security Group"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    # BUG: Open to the entire internet
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}-db"
  engine         = "postgres"
  # BUG: Using outdated PostgreSQL version
  engine_version = "12.5"
  instance_class = "db.t3.micro"

  db_name  = "appdb"
  username = "postgres"
  password = var.db_password

  allocated_storage     = 20
  max_allocated_storage = 100

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # BUG: Publicly accessible database
  publicly_accessible = true

  # BUG: Deletion protection disabled - database can be accidentally deleted
  deletion_protection = false

  # BUG: No automated backups
  backup_retention_period = 0

  # BUG: No encryption at rest
  storage_encrypted = false

  # BUG: No performance insights
  performance_insights_enabled = false

  # BUG: No enhanced monitoring
  monitoring_interval = 0

  # BUG: Auto minor version upgrades disabled
  auto_minor_version_upgrade = false

  # BUG: Multi-AZ disabled - no high availability
  multi_az = false

  skip_final_snapshot = true

  tags = var.tags
}

# BUG: Read replica in same AZ as primary - defeats purpose
resource "aws_db_instance" "replica" {
  identifier             = "${var.project_name}-${var.environment}-db-replica"
  replicate_source_db    = aws_db_instance.main.identifier
  instance_class         = "db.t3.micro"
  publicly_accessible    = true
  # BUG: Replica in same availability zone as primary
  availability_zone      = "us-east-1a"
  skip_final_snapshot    = true
  storage_encrypted      = false

  tags = var.tags
}

output "db_endpoint" {
  value = aws_db_instance.main.endpoint
}

# BUG: Outputs DB password in plaintext
output "db_password" {
  value     = var.db_password
  sensitive = false  # BUG: Should be sensitive = true
}
