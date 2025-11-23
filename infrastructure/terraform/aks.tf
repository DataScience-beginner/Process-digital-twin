# Azure Kubernetes Service (AKS) Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "refinerydt-dev-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "refinerydt-dev"
  
  # Kubernetes version - Latest stable
  kubernetes_version = "1.33.5"
  
  # Default node pool (system)
  default_node_pool {
    name                = "system"
    node_count          = 1
    vm_size             = "Standard_D2s_v3"  # Changed from B2s
    os_disk_size_gb     = 30
    type                = "VirtualMachineScaleSets"
    enable_auto_scaling = false
  }
  
  # Managed identity
  identity {
    type = "SystemAssigned"
  }
  
  # Network profile
  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.0.0.0/16"
    dns_service_ip    = "10.0.0.10"
  }
  
  tags = var.tags
}

# Outputs
output "aks_cluster_name" {
  value       = azurerm_kubernetes_cluster.aks.name
  description = "AKS cluster name"
}

output "aks_get_credentials_command" {
  value       = "az aks get-credentials --resource-group ${azurerm_resource_group.main.name} --name ${azurerm_kubernetes_cluster.aks.name}"
  description = "Command to configure kubectl"
}
