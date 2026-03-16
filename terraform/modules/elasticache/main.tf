variable "project_name" {}
variable "environment" {}
variable "vpc_id" {}
variable "subnet_ids" {}
variable "tags" { default = {} }

# BUG: Security group allows Redis access from anywhere
resource "aws_security_group" "redis" {
  name        = "${var.project_name}-${var.environment}-redis-sg"
  description = "ElastiCache Redis Security Group"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 6379
    to_port     = 6379
    protocol    = "tcp"
    # BUG: Open to entire internet
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = var.tags
}

resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-redis-subnet"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.project_name}-${var.environment}-redis"
  engine               = "redis"
  # BUG: Using outdated Redis version
  engine_version       = "5.0.6"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis5.0"
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  # BUG: No encryption in transit
  # transit_encryption_enabled = true  # commented out

  # BUG: No encryption at rest
  at_rest_encryption_enabled = false

  # BUG: No auth token - anyone can connect to Redis
  # auth_token = ...

  # BUG: Automatic failover disabled
  # automatic_failover_enabled = false  # N/A for single node but no replication group

  tags = var.tags
}

output "endpoint" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].address
}

output "port" {
  value = aws_elasticache_cluster.redis.cache_nodes[0].port
}
