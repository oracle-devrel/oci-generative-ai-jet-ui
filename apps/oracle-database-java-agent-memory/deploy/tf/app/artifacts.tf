data "archive_file" "ansible_ops_artifact" {
  type             = "zip"
  source_dir       = "${path.module}/../../ansible/ops"
  output_file_mode = "0666"
  output_path      = "${path.module}/generated/ansible_ops_artifact.zip"
}

data "archive_file" "ansible_backend_artifact" {
  type             = "zip"
  source_dir       = "${path.module}/../../ansible/backend"
  output_file_mode = "0666"
  output_path      = "${path.module}/generated/ansible_backend_artifact.zip"
}

data "archive_file" "ansible_web_artifact" {
  type             = "zip"
  source_dir       = "${path.module}/../../ansible/web"
  output_file_mode = "0666"
  output_path      = "${path.module}/generated/ansible_web_artifact.zip"
}

data "archive_file" "ansible_ollama_artifact" {
  type             = "zip"
  source_dir       = "${path.module}/../../ansible/ollama"
  output_file_mode = "0666"
  output_path      = "${path.module}/generated/ansible_ollama_artifact.zip"
}

data "archive_file" "backend_jar_artifact" {
  type             = "zip"
  source_file      = "${path.module}/../../../src/chatserver/build/libs/chatserver-0.0.1-SNAPSHOT.jar"
  output_file_mode = "0666"
  output_path      = "${path.module}/generated/backend_jar_artifact.zip"
}

data "archive_file" "web_streamlit_artifact" {
  type             = "zip"
  source_dir       = "${path.module}/../../../src/web"
  output_file_mode = "0666"
  output_path      = "${path.module}/generated/web_streamlit_artifact.zip"
  excludes = [
    "venv",
    "__pycache__",
  ]
}
