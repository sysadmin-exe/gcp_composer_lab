resource "google_project" "gcpComposer" {
  name                = var.projectName
  project_id          = var.projectId
  auto_create_network = "false"
}