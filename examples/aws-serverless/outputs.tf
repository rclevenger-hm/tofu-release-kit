output "health_url" {
  description = "Readiness endpoint; reports application revision and checks table availability."
  value       = "${aws_apigatewayv2_api.api.api_endpoint}/health"
}

output "application_revision" {
  description = "Expected revision to match in the deployed health response."
  value       = var.application_revision
}
