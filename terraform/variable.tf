variable "projectName" {
    description = "GCP Project Name"
    default     = "tf test Project"
}

variable "projectId" {
    description = "GCP Project ID"
    default     = "tf-project-lab-238972"
}

variable "projectRegion" {
    description = "GCP Composer Region"
    default     = "us-central1"
}


variable "gcpComposerNetworkName" {
    description = "GCP Composer Network Name"
    default     = "composer-test-network"
}

variable "gcpComposerSubnetName" {
    description = "GCP Composer Subnet Name"
    default     = "composer-test-subnetwork"
}

variable "gcpComposerSubnetCIDR" {
    description = "GCP Composer Subnet CIDR"
    default     = "10.2.0.0/16"
}