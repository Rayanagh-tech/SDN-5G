# ============================================================================
# Terraform Outputs for 5G Network Slicing Lab
# ============================================================================
# These outputs provide useful information after deployment.
# Access using: terraform output <output_name>
# ============================================================================

# ----------------------------------------------------------------------------
# ELK Stack Endpoints
# ----------------------------------------------------------------------------
output "elasticsearch_url" {
  description = "Elasticsearch HTTP endpoint"
  value       = "http://localhost:9200"
}

output "kibana_url" {
  description = "Kibana web interface URL"
  value       = "http://localhost:5601"
}

output "logstash_http_endpoint" {
  description = "Logstash HTTP input endpoint for metrics"
  value       = "http://localhost:5044"
}

output "logstash_beats_endpoint" {
  description = "Logstash Beats input endpoint"
  value       = "localhost:5045"
}

# ----------------------------------------------------------------------------
# Ryu Controller Endpoints (if deployed in container)
# ----------------------------------------------------------------------------
output "ryu_openflow_endpoint" {
  description = "Ryu OpenFlow controller endpoint"
  value       = var.deploy_ryu_container ? "tcp://localhost:6653" : "Not deployed in container - run locally"
}

output "ryu_api_endpoint" {
  description = "Ryu REST API endpoint"
  value       = var.deploy_ryu_container ? "http://localhost:8080" : "http://localhost:8080 (when running locally)"
}

# ----------------------------------------------------------------------------
# Network Information
# ----------------------------------------------------------------------------
output "docker_network_name" {
  description = "Name of the Docker network"
  value       = docker_network.sdn_network.name
}

output "docker_network_subnet" {
  description = "Docker network subnet"
  value       = var.sdn_network_subnet
}

output "container_ips" {
  description = "IP addresses of deployed containers"
  value = {
    elasticsearch = "172.28.0.10"
    logstash      = "172.28.0.11"
    kibana        = "172.28.0.12"
    ryu           = var.deploy_ryu_container ? "172.28.0.20" : "N/A"
  }
}

# ----------------------------------------------------------------------------
# Container Status
# ----------------------------------------------------------------------------
output "elasticsearch_container_id" {
  description = "Elasticsearch container ID"
  value       = docker_container.elasticsearch.id
}

output "logstash_container_id" {
  description = "Logstash container ID"
  value       = docker_container.logstash.id
}

output "kibana_container_id" {
  description = "Kibana container ID"
  value       = docker_container.kibana.id
}

# ----------------------------------------------------------------------------
# Quick Start Instructions
# ----------------------------------------------------------------------------
output "quick_start" {
  description = "Quick start instructions for the lab"
  value = <<-EOT

================================================================================
5G NETWORK SLICING LAB - DEPLOYMENT COMPLETE
================================================================================

ENDPOINTS:
  - Kibana Dashboard:     http://localhost:5601
  - Elasticsearch API:    http://localhost:9200
  - Logstash Metrics:     http://localhost:5044

NEXT STEPS:

1. Start the Ryu SDN Controller:
   $ cd ${abspath(path.module)}/..
   $ ryu-manager --ofp-tcp-listen-port 6653 --wsapi-port 8080 controller.py

2. Start Mininet Topology (requires sudo):
   $ sudo python3 topology.py

3. Run Traffic Generation:
   $ python3 -m traffic.traffic_generator --server 10.0.0.100 --duration 60

4. Start Metrics Collection:
   $ python3 monitoring/metrics_collector.py --duration 120

5. View Results in Kibana:
   - Open http://localhost:5601
   - Go to "Discover" and select "sdn-*" index pattern
   - Create visualizations in "Visualize Library"

USEFUL COMMANDS:
  - Check container status:  docker ps -a --filter label=project=5g-network-slicing
  - View Elasticsearch logs: docker logs elasticsearch
  - View Logstash logs:      docker logs logstash
  - Stop all containers:     docker stop elasticsearch logstash kibana

================================================================================
EOT
}

# ----------------------------------------------------------------------------
# Configuration Summary
# ----------------------------------------------------------------------------
output "configuration_summary" {
  description = "Summary of the deployment configuration"
  value = {
    elk_version       = var.elk_version
    resource_profile  = var.resource_profile
    ryu_containerized = var.deploy_ryu_container
    project           = var.project_name
    environment       = var.environment
  }
}
