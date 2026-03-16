# Dummy Infrastructure Project

A complex dummy infrastructure project containing intentional bugs for AI model testing and code review practice.

## ⚠️ WARNING

**This is a DUMMY project intentionally filled with bugs, security vulnerabilities, and anti-patterns.**
**Do NOT use any code from this repository in production.**

---

## Project Overview

This project simulates a real-world microservices-based e-commerce backend running on AWS, with Kubernetes orchestration and GitHub Actions CI/CD pipelines.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    API Gateway (:8000)                   │
│              (Routes to all microservices)               │
└────────┬──────────┬──────────┬──────────┬───────────────┘
         │          │          │          │
         ▼          ▼          ▼          ▼
   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐
   │  User    │ │  Order   │ │  Auth    │ │Notification  │
   │ Service  │ │ Service  │ │ Service  │ │  Service     │
   │ (:8001)  │ │ (:8002)  │ │ (:8003)  │ │  (:8004)     │
   └────┬─────┘ └────┬─────┘ └──────────┘ └──────────────┘
        │             │
        ▼             ▼
   ┌──────────┐  ┌──────────┐
   │PostgreSQL│  │  Redis   │
   │  (:5432) │  │  (:6379) │
   └──────────┘  └──────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| API Gateway | 8000 | Routes requests to downstream services |
| User Service | 8001 | User management (CRUD) |
| Order Service | 8002 | Order lifecycle management |
| Auth Service | 8003 | Authentication & JWT tokens |
| Notification Service | 8004 | Email & SMS notifications |

## Technology Stack

- **Backend**: Python/Flask
- **Database**: PostgreSQL, SQLite (dev), Redis
- **Infrastructure**: AWS (ECS, RDS, S3, ElastiCache, VPC, IAM)
- **IaC**: Terraform
- **Orchestration**: Kubernetes (EKS) with Kustomize
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus, Grafana, PagerDuty
- **Containerization**: Docker, Docker Compose

## Directory Structure

```
dummy-infra-project/
├── .github/workflows/          # CI/CD pipelines
│   ├── build.yml               # Build & push Docker images
│   ├── test.yml                # Run tests
│   ├── deploy.yml              # Deploy to Kubernetes
│   └── infra.yml               # Terraform infrastructure
├── backend/                    # Microservices
│   ├── api-gateway/            # API Gateway service
│   ├── user-service/           # User management
│   ├── order-service/          # Order management
│   ├── auth-service/           # Authentication
│   └── notification-service/   # Notifications
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                 # Root module
│   ├── modules/
│   │   ├── vpc/                # VPC, subnets, security groups
│   │   ├── ecs/                # ECS cluster and services
│   │   ├── rds/                # RDS PostgreSQL
│   │   ├── s3/                 # S3 buckets
│   │   ├── elasticache/        # Redis ElastiCache
│   │   └── iam/                # IAM roles and policies
│   └── environments/
│       ├── dev/                # Dev environment
│       └── prod/               # Production environment
├── kubernetes/                 # K8s manifests
│   ├── base/
│   │   ├── deployments/        # Deployment manifests
│   │   ├── services/           # Service manifests
│   │   ├── configmaps/         # ConfigMaps & Secrets
│   │   └── ingress/            # Ingress & HPA
│   └── overlays/
│       ├── dev/                # Dev kustomization
│       └── prod/               # Prod kustomization
├── monitoring/                 # Monitoring config
│   ├── prometheus.yml          # Prometheus config
│   ├── alerts.yml              # Alert rules
│   └── alerts.py               # Alert routing
├── migrations/                 # DB migrations
│   └── migrate.py
├── scripts/                    # Operational scripts
│   ├── deploy.sh               # Deployment script
│   ├── migrate.sh              # Migration script
│   └── health_check.sh         # Health check script
├── tests/                      # Test suite
│   ├── test_api_gateway.py
│   ├── test_user_service.py
│   ├── test_order_service.py
│   └── test_auth_service.py
├── config/                     # Environment configs
│   ├── dev.env
│   └── prod.env
└── docker-compose.yml          # Local development
```

## Known Bugs (Intentional)

This project contains numerous intentional bugs for testing purposes. Categories include:

### Security Vulnerabilities
- SQL injection in User Service queries
- Hardcoded secrets (JWT keys, DB passwords, API keys) throughout
- MD5 password hashing (no salt)
- JWT tokens never expire
- Auth service returns `valid=True` when no token provided
- S3 buckets publicly accessible with write permissions
- IAM roles with `AdministratorAccess`
- Database exposed to the public internet

### Logic Bugs
- Off-by-one in user stats (inactive count)
- Tax rate 10x too high (10 instead of 0.10)
- SAVE discount gives 100% off on any order
- Order status machine allows invalid transitions
- API Gateway returns HTTP 200 on service timeout (should be 504)
- Order "not found" returns HTTP 200 (should be 404)

### Configuration Issues
- Wrong ports in Docker/K8s configs (app port vs exposed port mismatch)
- Dev and prod Terraform environments share the same state file
- API Gateway applies dev Kubernetes overlay to production
- Health check script always exits 0 regardless of service status
- Pre-deploy checks run AFTER deployment (too late)
- Smoke tests ignore failures

### Infrastructure Issues
- Database in public subnet
- Redis accessible without authentication
- No NAT gateway for private subnets
- ECS tasks in public subnets with public IPs
- No multi-AZ for RDS
- No automated backups
- No encryption at rest for RDS or Redis
- Container Insights disabled
- Auto-scaling triggers at 90-95% CPU (too late)

### CI/CD Issues
- AWS credentials hardcoded in workflow files
- Builds trigger on ALL branches
- No image vulnerability scanning
- Test failures masked with `|| true`
- No manual approval for production deployments
- `build-summary` job runs without waiting for builds

## Local Development

```bash
# Start all services
docker-compose up -d

# Run tests
pip install -r tests/requirements.txt
pytest tests/ -v

# Run database migrations
python migrations/migrate.py

# Check service health
bash scripts/health_check.sh
```

## API Endpoints

### User Service
| Method | Path | Description |
|--------|------|-------------|
| GET | /users | List all users (no auth) |
| POST | /users | Create user |
| GET | /users/{id} | Get user |
| PUT | /users/{id} | Update user (no auth) |
| DELETE | /users/{id} | Delete user (no auth) |
| GET | /users/search?q= | Search users |

### Order Service
| Method | Path | Description |
|--------|------|-------------|
| POST | /orders | Create order |
| GET | /orders/{id} | Get order |
| PUT | /orders/{id}/status | Update status |
| GET | /orders/user/{id} | Get user orders |
| GET | /orders/metrics | Order metrics |

### Auth Service
| Method | Path | Description |
|--------|------|-------------|
| POST | /login | Login |
| GET | /validate | Validate token |
| POST | /logout | Logout |
| POST | /refresh | Refresh token |

### Notification Service
| Method | Path | Description |
|--------|------|-------------|
| POST | /notify/email | Send email |
| POST | /notify/sms | Send SMS |
| POST | /notify/bulk | Bulk notifications |
| GET | /notifications/{user_id} | Get notification history |