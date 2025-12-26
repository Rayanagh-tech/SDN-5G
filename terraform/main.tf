# ============================================================================
# Terraform Configuration for 5G Network Slicing Lab Environment
# ============================================================================
# This configuration deploys the complete 5G Network Slicing infrastructure
# using Docker containers on a local machine.
#
# Components:
# - ELK Stack (Elasticsearch, Logstash, Kibana)
# - Ryu SDN Controller container
# - Mininet container (optional, for containerized deployment)
#
# Usage:
#   terraform init
#   terraform plan
#   terraform apply
#   terraform destroy
# ============================================================================

terraform {
  required_version = ">= 1.0.0"
  
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
    }
  }
}

# ----------------------------------------------------------------------------
# Provider Configuration
# ----------------------------------------------------------------------------
provider "docker" {
  # Use local Docker socket
  # On Windows with Docker Desktop, this works automatically
  # On Linux, ensure the socket is accessible
  host = var.docker_host
}

# ----------------------------------------------------------------------------
# Docker Network
# ----------------------------------------------------------------------------
resource "docker_network" "sdn_network" {
  name   = "sdn-slicing-network"
  driver = "bridge"
  
  ipam_config {
    subnet  = "172.28.0.0/16"
    gateway = "172.28.0.1"
  }
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
}

# ----------------------------------------------------------------------------
# Docker Volumes for Persistent Data
# ----------------------------------------------------------------------------
resource "docker_volume" "elasticsearch_data" {
  name = "elasticsearch-data"
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
}

resource "docker_volume" "logstash_pipeline" {
  name = "logstash-pipeline"
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
}

resource "docker_volume" "metrics_data" {
  name = "metrics-data"
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
}

# ----------------------------------------------------------------------------
# Elasticsearch Container
# ----------------------------------------------------------------------------
resource "docker_image" "elasticsearch" {
  name         = "docker.elastic.co/elasticsearch/elasticsearch:${var.elk_version}"
  keep_locally = true
}

resource "docker_container" "elasticsearch" {
  name  = "elasticsearch"
  image = docker_image.elasticsearch.image_id
  
  restart = "unless-stopped"
  
  env = [
    "discovery.type=single-node",
    "ES_JAVA_OPTS=-Xms${var.elasticsearch_heap} -Xmx${var.elasticsearch_heap}",
    "xpack.security.enabled=false",
    "xpack.monitoring.collection.enabled=true"
  ]
  
  ports {
    internal = 9200
    external = 9200
  }
  
  ports {
    internal = 9300
    external = 9300
  }
  
  volumes {
    volume_name    = docker_volume.elasticsearch_data.name
    container_path = "/usr/share/elasticsearch/data"
  }
  
  networks_advanced {
    name         = docker_network.sdn_network.name
    ipv4_address = "172.28.0.10"
  }
  
  memory = var.elasticsearch_memory
  
  healthcheck {
    test         = ["CMD-SHELL", "curl -s http://localhost:9200 || exit 1"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 5
    start_period = "60s"
  }
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
  
  labels {
    label = "component"
    value = "elasticsearch"
  }
}

# ----------------------------------------------------------------------------
# Logstash Container
# ----------------------------------------------------------------------------
resource "docker_image" "logstash" {
  name         = "docker.elastic.co/logstash/logstash:${var.elk_version}"
  keep_locally = true
}

resource "docker_container" "logstash" {
  name  = "logstash"
  image = docker_image.logstash.image_id
  
  restart = "unless-stopped"
  
  depends_on = [docker_container.elasticsearch]
  
  env = [
    "LS_JAVA_OPTS=-Xms${var.logstash_heap} -Xmx${var.logstash_heap}",
    "ELASTICSEARCH_HOSTS=http://elasticsearch:9200"
  ]
  
  ports {
    internal = 5044
    external = 5044
  }
  
  ports {
    internal = 5045
    external = 5045
  }
  
  ports {
    internal = 9600
    external = 9600
  }
  
  # Mount Logstash configuration
  volumes {
    host_path      = abspath("${path.module}/../monitoring/logstash.conf")
    container_path = "/usr/share/logstash/pipeline/logstash.conf"
    read_only      = true
  }
  
  # Mount metrics directory
  volumes {
    host_path      = abspath("${path.module}/../monitoring/metrics")
    container_path = "/app/metrics"
  }
  
  # Mount logs directory
  volumes {
    host_path      = abspath("${path.module}/../monitoring/logs")
    container_path = "/app/logs"
  }
  
  networks_advanced {
    name         = docker_network.sdn_network.name
    ipv4_address = "172.28.0.11"
  }
  
  memory = var.logstash_memory
  
  healthcheck {
    test         = ["CMD-SHELL", "curl -s http://localhost:9600 || exit 1"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 5
    start_period = "60s"
  }
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
  
  labels {
    label = "component"
    value = "logstash"
  }
}

# ----------------------------------------------------------------------------
# Kibana Container
# ----------------------------------------------------------------------------
resource "docker_image" "kibana" {
  name         = "docker.elastic.co/kibana/kibana:${var.elk_version}"
  keep_locally = true
}

resource "docker_container" "kibana" {
  name  = "kibana"
  image = docker_image.kibana.image_id
  
  restart = "unless-stopped"
  
  depends_on = [docker_container.elasticsearch]
  
  env = [
    "ELASTICSEARCH_HOSTS=http://elasticsearch:9200",
    "SERVER_NAME=kibana",
    "XPACK_SECURITY_ENABLED=false"
  ]
  
  ports {
    internal = 5601
    external = 5601
  }
  
  networks_advanced {
    name         = docker_network.sdn_network.name
    ipv4_address = "172.28.0.12"
  }
  
  memory = var.kibana_memory
  
  healthcheck {
    test         = ["CMD-SHELL", "curl -s http://localhost:5601/api/status || exit 1"]
    interval     = "30s"
    timeout      = "10s"
    retries      = 5
    start_period = "120s"
  }
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
  
  labels {
    label = "component"
    value = "kibana"
  }
}

# ----------------------------------------------------------------------------
# Ryu SDN Controller Container (Optional - for containerized deployment)
# ----------------------------------------------------------------------------
resource "docker_image" "ryu" {
  count = var.deploy_ryu_container ? 1 : 0
  
  name         = "osrg/ryu:latest"
  keep_locally = true
}

resource "docker_container" "ryu_controller" {
  count = var.deploy_ryu_container ? 1 : 0
  
  name  = "ryu-controller"
  image = docker_image.ryu[0].image_id
  
  restart = "unless-stopped"
  
  # Mount controller code
  volumes {
    host_path      = abspath("${path.module}/..")
    container_path = "/app"
    read_only      = false
  }
  
  working_dir = "/app"
  
  # Run Ryu with our controller
  command = [
    "ryu-manager",
    "--ofp-tcp-listen-port", "6653",
    "--wsapi-port", "8080",
    "controller.py"
  ]
  
  ports {
    internal = 6653
    external = 6653
  }
  
  ports {
    internal = 8080
    external = 8080
  }
  
  networks_advanced {
    name         = docker_network.sdn_network.name
    ipv4_address = "172.28.0.20"
  }
  
  labels {
    label = "project"
    value = "5g-network-slicing"
  }
  
  labels {
    label = "component"
    value = "ryu-controller"
  }
}

# ----------------------------------------------------------------------------
# Create Required Directories
# ----------------------------------------------------------------------------
resource "null_resource" "create_directories" {
  provisioner "local-exec" {
    command     = "New-Item -ItemType Directory -Force -Path '${path.module}/../monitoring/metrics', '${path.module}/../monitoring/logs'"
    interpreter = ["PowerShell", "-Command"]
  }
}

# ----------------------------------------------------------------------------
# Wait for ELK Stack to be Ready
# ----------------------------------------------------------------------------
resource "null_resource" "wait_for_elk" {
  depends_on = [
    docker_container.elasticsearch,
    docker_container.logstash,
    docker_container.kibana
  ]
  
  provisioner "local-exec" {
    command = <<-EOT
      Write-Host "Waiting for ELK stack to be ready..."
      $maxAttempts = 30
      $attempt = 0
      do {
        $attempt++
        Start-Sleep -Seconds 10
        try {
          $response = Invoke-WebRequest -Uri "http://localhost:9200" -UseBasicParsing -TimeoutSec 5
          if ($response.StatusCode -eq 200) {
            Write-Host "Elasticsearch is ready!"
            break
          }
        } catch {
          Write-Host "Attempt $attempt/$maxAttempts - Elasticsearch not ready yet..."
        }
      } while ($attempt -lt $maxAttempts)
    EOT
    interpreter = ["PowerShell", "-Command"]
  }
}

# ----------------------------------------------------------------------------
# Create Elasticsearch Index Templates
# ----------------------------------------------------------------------------
resource "null_resource" "create_index_templates" {
  depends_on = [null_resource.wait_for_elk]
  
  provisioner "local-exec" {
    command = <<-EOT
      Start-Sleep -Seconds 5
      
      # Create index template for SDN metrics
      $template = @{
        index_patterns = @("sdn-*")
        template = @{
          settings = @{
            number_of_shards = 1
            number_of_replicas = 0
          }
          mappings = @{
            properties = @{
              timestamp = @{ type = "date" }
              slice_name = @{ type = "keyword" }
              bandwidth_mbps = @{ type = "float" }
              latency_ms = @{ type = "float" }
              jitter_ms = @{ type = "float" }
              packet_loss_pct = @{ type = "float" }
              packets = @{ type = "long" }
              bytes = @{ type = "long" }
              sla_status = @{ type = "keyword" }
              sla_violation = @{ type = "boolean" }
            }
          }
        }
      } | ConvertTo-Json -Depth 10
      
      try {
        Invoke-RestMethod -Uri "http://localhost:9200/_index_template/sdn-metrics" -Method PUT -Body $template -ContentType "application/json"
        Write-Host "Index template created successfully"
      } catch {
        Write-Host "Warning: Could not create index template: $_"
      }
    EOT
    interpreter = ["PowerShell", "-Command"]
  }
}
