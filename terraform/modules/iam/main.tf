variable "project_name" {}
variable "environment" {}

# BUG: Overly permissive IAM role - allows all AWS actions
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# BUG: Task role has full AdministratorAccess - violates least privilege
resource "aws_iam_role_policy_attachment" "ecs_admin" {
  role       = aws_iam_role.ecs_task_role.name
  # BUG: Should be custom minimal policy, not AdministratorAccess
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}

# BUG: EC2 instance profile also with admin access
resource "aws_iam_role" "ec2_instance_role" {
  name = "${var.project_name}-${var.environment}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "ec2_policy" {
  name = "${var.project_name}-ec2-policy"
  role = aws_iam_role.ec2_instance_role.id

  # BUG: Wildcard permissions on all resources
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "*"  # BUG: All actions allowed
        Resource = "*"  # BUG: On all resources
      }
    ]
  })
}

# BUG: CI/CD role also overly permissive
resource "aws_iam_user" "cicd" {
  name = "${var.project_name}-cicd-user"
  # BUG: IAM user for CI/CD instead of OIDC - long-lived credentials
}

resource "aws_iam_user_policy" "cicd_policy" {
  name = "${var.project_name}-cicd-policy"
  user = aws_iam_user.cicd.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        # BUG: CI/CD has full access to ECR, ECS, and S3
        Action   = ["ecr:*", "ecs:*", "s3:*", "iam:*"]
        Resource = "*"
      }
    ]
  })
}

output "ecs_task_role_arn" {
  value = aws_iam_role.ecs_task_role.arn
}
