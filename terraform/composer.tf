resource "google_composer_environment" "gcpComposer" {
  name   = "mycomposer"
  region = "us-central1"
  config {
    node_count = 3

    node_config {
      zone         = "us-central1-a"
      machine_type = "e2-medium"

      network    = google_compute_network.gcpComposer.id
      subnetwork = google_compute_subnetwork.gcpComposer.id

      service_account = google_service_account.gcpComposer.name
    }
    
    # Airflow Software config
    software_config {
      airflow_config_overrides = {
        core-load_example = "True"
      }

      pypi_packages = {
        numpy = ""
        scipy = "==1.1.0"
      }

      env_variables = {
        FOO = "bar"
      }
    }
  }
}

resource "google_service_account" "gcpComposer" {
  account_id   = "composer-env-account"
  display_name = "Test Service Account for Composer Environment"
}

resource "google_project_iam_member" "composer-worker" {
  role   = "roles/composer.worker"
  member = "serviceAccount:${google_service_account.gcpComposer.email}"
}