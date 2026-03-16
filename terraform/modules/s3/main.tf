variable "project_name" {}
variable "environment" {}
variable "tags" { default = {} }

# BUG: S3 bucket with public access allowed
resource "aws_s3_bucket" "assets" {
  # BUG: Bucket name uses environment but no random suffix - name collision risk
  bucket = "${var.project_name}-${var.environment}-assets"

  tags = var.tags
}

# BUG: Public access block disabled - bucket contents publicly accessible
resource "aws_s3_bucket_public_access_block" "assets" {
  bucket = aws_s3_bucket.assets.id

  block_public_acls       = false  # BUG: Should be true
  block_public_policy     = false  # BUG: Should be true
  ignore_public_acls      = false  # BUG: Should be true
  restrict_public_buckets = false  # BUG: Should be true
}

# BUG: Overly permissive bucket policy
resource "aws_s3_bucket_policy" "assets" {
  bucket = aws_s3_bucket.assets.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadWrite"
        Effect    = "Allow"
        Principal = "*"  # BUG: Allows anyone
        Action    = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]  # BUG: Write access to public
        Resource  = "${aws_s3_bucket.assets.arn}/*"
      }
    ]
  })
}

# BUG: No versioning enabled
resource "aws_s3_bucket_versioning" "assets" {
  bucket = aws_s3_bucket.assets.id
  versioning_configuration {
    status = "Disabled"  # BUG: Should be Enabled
  }
}

# BUG: No server-side encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "assets" {
  bucket = aws_s3_bucket.assets.id
  # BUG: Rule block missing - no encryption configured
}

# Logs bucket
resource "aws_s3_bucket" "logs" {
  bucket = "${var.project_name}-${var.environment}-logs"
  # BUG: No lifecycle policy to delete old logs - costs grow unbounded

  tags = var.tags
}

# BUG: Logs bucket also public
resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

output "assets_bucket_name" {
  value = aws_s3_bucket.assets.bucket
}

output "logs_bucket_name" {
  value = aws_s3_bucket.logs.bucket
}

output "assets_bucket_arn" {
  value = aws_s3_bucket.assets.arn
}
