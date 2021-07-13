terraform {
  backend "gcs" {
    bucket  = "pristine-cairn-318322"
    prefix  = "terraform/state"
  }
}