variable "project_name" {
  description = "Project name"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  # BUG: Default CIDR overlaps with common corporate ranges
  default     = "10.0.0.0/8"
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default     = {}
}

resource "aws_vpc" "main" {
  cidr_block = var.vpc_cidr

  # BUG: DNS hostnames disabled - breaks service discovery
  enable_dns_hostnames = false
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-${var.environment}-vpc"
  })
}

# BUG: Only 2 AZs - not highly available for production (should be 3)
resource "aws_subnet" "public" {
  count = 2

  vpc_id            = aws_vpc.main.id
  # BUG: Subnet CIDR calculation may produce overlapping ranges
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone = "us-east-1${count.index == 0 ? "a" : "b"}"

  # BUG: Auto-assigning public IPs to all instances in subnet
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.project_name}-public-${count.index}"
    Tier = "public"
  })
}

resource "aws_subnet" "private" {
  count = 2

  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = "us-east-1${count.index == 0 ? "a" : "b"}"

  map_public_ip_on_launch = false

  tags = merge(var.tags, {
    Name = "${var.project_name}-private-${count.index}"
    Tier = "private"
  })
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.tags, {
    Name = "${var.project_name}-igw"
  })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# BUG: No NAT Gateway for private subnets - private instances can't reach internet
# BUG: Security group allows all traffic from anywhere
resource "aws_security_group" "default" {
  name        = "${var.project_name}-${var.environment}-default-sg"
  description = "Default security group"
  vpc_id      = aws_vpc.main.id

  # BUG: Allows all inbound traffic from anywhere
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # BUG: Allows all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-default-sg"
  })
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "default_security_group_id" {
  value = aws_security_group.default.id
}
