# ============================================================================
# Terraform Variables for 5G Network Slicing Lab
# ============================================================================
# Customize these variables to adjust the deployment configuration.
# Override values using terraform.tfvars or -var command line arguments.
# ============================================================================

# ----------------------------------------------------------------------------
# Docker Provider Configuration
# ----------------------------------------------------------------------------
variable "docker_host" {
  description = "Docker host socket/endpoint"
  type        = string
  default     = "npipe:////.//pipe//docker_engine"
  # For Linux: "unix:///var/run/docker.sock"
  # For Windows with Docker Desktop: "npipe:////.//pipe//docker_engine"
  # For remote Docker: "tcp://host:2375"
}

# ----------------------------------------------------------------------------
# ELK Stack Version
# ----------------------------------------------------------------------------
variable "elk_version" {
  description = "Version of Elasticsearch, Logstash, and Kibana"
  type        = string
  default     = "8.11.0"
}

# ----------------------------------------------------------------------------
# Elasticsearch Configuration
# ----------------------------------------------------------------------------
variable "elasticsearch_heap" {
  description = "Elasticsearch JVM heap size"
  type        = string
  default     = "512m"
}

variable "elasticsearch_memory" {
  description = "Elasticsearch container memory limit (in bytes)"
  type        = number
  default     = 1073741824  # 1GB
}

# ----------------------------------------------------------------------------
# Logstash Configuration
# ----------------------------------------------------------------------------
variable "logstash_heap" {
  description = "Logstash JVM heap size"
  type        = string
  default     = "256m"
}

variable "logstash_memory" {
  description = "Logstash container memory limit (in bytes)"
  type        = number
  default     = 536870912  # 512MB
}

# ----------------------------------------------------------------------------
# Kibana Configuration
# ----------------------------------------------------------------------------
variable "kibana_memory" {
  description = "Kibana container memory limit (in bytes)"
  type        = number
  default     = 536870912  # 512MB
}

# ----------------------------------------------------------------------------
# Ryu Controller Configuration
# ----------------------------------------------------------------------------
variable "deploy_ryu_container" {
  description = "Whether to deploy Ryu controller in a container"
  type        = bool
  default     = false
  # Set to false if running Ryu directly on the host
  # Set to true for fully containerized deployment
}

variable "ryu_openflow_port" {
  description = "OpenFlow port for Ryu controller"
  type        = number
  default     = 6653
}

variable "ryu_api_port" {
  description = "REST API port for Ryu controller"
  type        = number
  default     = 8080
}

# ----------------------------------------------------------------------------
# Network Configuration
# ----------------------------------------------------------------------------
variable "sdn_network_subnet" {
  description = "Subnet for SDN Docker network"
  type        = string
  default     = "172.28.0.0/16"
}

variable "sdn_network_gateway" {
  description = "Gateway for SDN Docker network"
  type        = string
  default     = "172.28.0.1"
}

# ----------------------------------------------------------------------------
# Resource Limits (for constrained environments)
# ----------------------------------------------------------------------------
variable "resource_profile" {
  description = "Resource profile: minimal, standard, or production"
  type        = string
  default     = "standard"
  
  validation {
    condition     = contains(["minimal", "standard", "production"], var.resource_profile)
    error_message = "Resource profile must be one of: minimal, standard, production"
  }
}

# Computed resource values based on profile
locals {
  resource_profiles = {
    minimal = {
      elasticsearch_heap   = "256m"
      elasticsearch_memory = 536870912  # 512MB
      logstash_heap        = "128m"
      logstash_memory      = 268435456  # 256MB
      kibana_memory        = 268435456  # 256MB
    }
    standard = {
      elasticsearch_heap   = "512m"
      elasticsearch_memory = 1073741824  # 1GB
      logstash_heap        = "256m"
      logstash_memory      = 536870912   # 512MB
      kibana_memory        = 536870912   # 512MB
    }
    production = {
      elasticsearch_heap   = "2g"
      elasticsearch_memory = 4294967296  # 4GB
      logstash_heap        = "1g"
      logstash_memory      = 2147483648  # 2GB
      kibana_memory        = 1073741824  # 1GB
    }
  }
  
  # Selected profile values (can be overridden by explicit variables)
  selected_profile = local.resource_profiles[var.resource_profile]
}

# ----------------------------------------------------------------------------
# Project Metadata
# ----------------------------------------------------------------------------
variable "project_name" {
  description = "Name of the project for resource labeling"
  type        = string
  default     = "5g-network-slicing"
}

variable "environment" {
  description = "Deployment environment (dev, test, prod)"
  type        = string
  default     = "dev"
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
  default     = "sdn-team"
}
