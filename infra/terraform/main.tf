# Terraform IaC: Multi-Cloud Production Fleet Infrastructure
# Demonstrates Cloud-Agnostic Portable Deployment per Section 5.4 & 13

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "db_master_password" {
  type      = string
  sensitive = true
}

# 1. High-Performance Aurora PostgreSQL (Multi-AZ with 3NF Schema)
resource "aws_rds_cluster" "aegis_postgres" {
  cluster_identifier      = "aegisfleet-aurora-cluster"
  engine                  = "aurora-postgresql"
  engine_version          = "16.1"
  database_name           = "aegis_fleet"
  master_username         = "aegisadmin"
  master_password         = var.db_master_password
  backup_retention_period = 14
  preferred_backup_window = "02:00-03:00"
  storage_encrypted       = true
  deletion_protection     = false
  skip_final_snapshot     = true
}

resource "aws_rds_cluster_instance" "cluster_instances" {
  count              = 2
  identifier         = "aegisfleet-db-node-${count.index}"
  cluster_identifier = aws_rds_cluster.aegis_postgres.id
  instance_class     = "db.r6g.xlarge"
  engine             = aws_rds_cluster.aegis_postgres.engine
  engine_version     = aws_rds_cluster.aegis_postgres.engine_version
}

# 2. Redis Elasticache Cluster (Bloom Filter Deduplication & In-Memory Hot State)
resource "aws_elasticache_cluster" "redis_cache" {
  cluster_id           = "aegisfleet-redis"
  engine               = "redis"
  node_type            = "cache.m6g.large"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
}

# 3. EKS Managed Kubernetes Cluster
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "aegisfleet-prod-eks"
  cluster_version = "1.29"

  vpc_id     = "vpc-0a1b2c3d4e5f67890"
  subnet_ids = ["subnet-01", "subnet-02", "subnet-03"]

  eks_managed_node_groups = {
    telemetry_workers = {
      min_size     = 3
      max_size     = 15
      desired_size = 5

      instance_types = ["c6i.2xlarge"]
      capacity_type  = "ON_DEMAND"
    }
  }
}
