#!/bin/bash
# Deployment script
# BUG: No error handling - script continues even if steps fail
# BUG: No rollback on failure
# BUG: Deploys directly to production without confirmation
# BUG: Uses hardcoded environment variables

set -e  # BUG: set -e will exit on any error but no cleanup trap

# BUG: Hardcoded values
AWS_REGION="us-east-1"
ECR_REGISTRY="123456789012.dkr.ecr.us-east-1.amazonaws.com"
EKS_CLUSTER="dummy-infra-prod"
# BUG: Hardcoded AWS credentials in script
AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# BUG: No environment argument - always deploys to prod
ENVIRONMENT="prod"

echo "Starting deployment to $ENVIRONMENT..."

# BUG: No check if required tools are installed
export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
export AWS_DEFAULT_REGION=$AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# BUG: Builds and pushes all images with same "latest" tag
# BUG: No image digest capture for deployment tracking
SERVICES=("api-gateway" "user-service" "order-service" "auth-service" "notification-service")

for service in "${SERVICES[@]}"; do
    echo "Building $service..."
    docker build -t $ECR_REGISTRY/$service:latest ./backend/$service/
    docker push $ECR_REGISTRY/$service:latest
    # BUG: No scan between build and push
done

# Update kubeconfig
aws eks update-kubeconfig --name $EKS_CLUSTER --region $AWS_REGION

# BUG: Applies dev overlay to production
kubectl apply -k kubernetes/overlays/dev/

# BUG: No wait for deployment to complete
# BUG: No verification of deployment success
echo "Deployment complete!"

# BUG: Smoke tests run but failures are ignored
echo "Running smoke tests..."
# BUG: Hardcoded IP address
curl -s http://10.0.1.100/health > /dev/null && echo "Health check passed" || echo "Health check failed (ignoring)"

# BUG: Script exits 0 even if deployment was problematic
exit 0
