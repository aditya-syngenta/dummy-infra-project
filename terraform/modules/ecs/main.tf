variable "project_name" {}
variable "environment" {}
variable "vpc_id" {}
variable "subnet_ids" {}
variable "tags" { default = {} }

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  # BUG: Container insights disabled - no monitoring
  setting {
    name  = "containerInsights"
    value = "disabled"
  }

  tags = var.tags
}

# BUG: Task definition uses too much CPU/memory for small tasks
resource "aws_ecs_task_definition" "api_gateway" {
  family                   = "${var.project_name}-api-gateway"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "4096"  # BUG: 4 vCPU for a simple API gateway
  memory                   = "8192"  # BUG: 8GB RAM for a simple proxy service

  # BUG: No task execution role - tasks can't pull ECR images
  # task_execution_role_arn = ...

  container_definitions = jsonencode([
    {
      name  = "api-gateway"
      # BUG: Using 'latest' tag - not reproducible
      image = "dummy-infra/api-gateway:latest"
      portMappings = [
        {
          containerPort = 5000  # BUG: Wrong port - app uses 8000
          protocol      = "tcp"
        }
      ]
      # BUG: No environment variables configured
      environment = []
      # BUG: No log configuration - logs go nowhere
      logConfiguration = null
      # BUG: No resource limits on container
    }
  ])

  tags = var.tags
}

resource "aws_ecs_task_definition" "user_service" {
  family                   = "${var.project_name}-user-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"

  container_definitions = jsonencode([
    {
      name  = "user-service"
      image = "dummy-infra/user-service:latest"
      portMappings = [
        {
          containerPort = 8001
          protocol      = "tcp"
        }
      ]
      environment = [
        # BUG: Hardcoded secrets in task definition (visible in AWS console)
        { name = "DB_PASSWORD", value = "Passw0rd123!" },
        { name = "JWT_SECRET", value = "my-super-secret-jwt-key-dont-share" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"  = "/ecs/user-service"
          "awslogs-region" = "us-east-1"
          # BUG: Missing stream prefix
        }
      }
    }
  ])

  tags = var.tags
}

# BUG: Service uses wrong load balancer target group
resource "aws_ecs_service" "api_gateway" {
  name            = "${var.project_name}-api-gateway"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api_gateway.arn
  # BUG: desired_count set to 1 - no high availability
  desired_count   = 1

  launch_type = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    # BUG: Assigning public IP to ECS tasks
    assign_public_ip = true
    security_groups  = []  # BUG: No security groups assigned
  }

  # BUG: No load balancer configured
  # BUG: No health check grace period
  # BUG: No deployment circuit breaker

  tags = var.tags
}

resource "aws_ecs_service" "user_service" {
  name            = "${var.project_name}-user-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.user_service.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    assign_public_ip = true
    security_groups  = []
  }

  tags = var.tags
}

# BUG: Auto-scaling configured with wrong metrics
resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 10
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api_gateway.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ecs_policy" {
  name               = "${var.project_name}-scaling-policy"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    # BUG: Scaling based on CPU at 90% - too late, should be 70%
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 90.0
    # BUG: Scale-in cooldown too short - causes thrashing
    scale_in_cooldown  = 30
    scale_out_cooldown = 60
  }
}

output "cluster_id" {
  value = aws_ecs_cluster.main.id
}

output "cluster_arn" {
  value = aws_ecs_cluster.main.arn
}
