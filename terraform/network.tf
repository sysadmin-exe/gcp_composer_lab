resource "google_compute_network" "gcpComposer" {
  name                    = var.gcpComposerNetworkName
  auto_create_subnetworks = false
  project                 = google_project.gcpComposer.id
}

resource "google_compute_subnetwork" "gcpComposer" {
  name          = var.gcpComposerSubnetName
  ip_cidr_range = var.gcpComposerSubnetCIDR
  region        = var.projectRegion
  network       = google_compute_network.gcpComposer.id
  project       = google_project.gcpComposer.id
}