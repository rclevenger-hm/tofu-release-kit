mock_provider "aws" {
  mock_resource "aws_iam_role" {
    defaults = {
      arn = "arn:aws:iam::123456789012:role/trk-test"
    }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = {
      arn = "arn:aws:dynamodb:us-east-2:123456789012:table/trk-test"
    }
  }
  mock_resource "aws_cloudwatch_log_group" {
    defaults = {
      arn = "arn:aws:logs:us-east-2:123456789012:log-group:/aws/lambda/trk-test"
    }
  }
  mock_resource "aws_lambda_function" {
    defaults = {
      invoke_arn = "arn:aws:apigateway:us-east-2:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-2:123456789012:function:trk-test/invocations"
    }
  }
  mock_resource "aws_apigatewayv2_api" {
    defaults = {
      api_endpoint  = "https://test.execute-api.us-east-2.amazonaws.com"
      execution_arn = "arn:aws:execute-api:us-east-2:123456789012:test"
    }
  }
}

variables {
  owner                = "platform"
  environment          = "sandbox"
  application_revision = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
}

run "secure_defaults" {
  command = plan
  assert {
    condition     = aws_dynamodb_table.orders.server_side_encryption[0].enabled
    error_message = "Table encryption must remain enabled."
  }
  assert {
    condition     = aws_dynamodb_table.orders.point_in_time_recovery[0].enabled
    error_message = "Point-in-time recovery must remain enabled."
  }
  assert {
    condition     = aws_cloudwatch_log_group.api.retention_in_days == 7
    error_message = "The demo must bound log retention."
  }
  assert {
    condition     = aws_lambda_function.api.environment[0].variables["REVISION"] == var.application_revision
    error_message = "The deployed application must expose the requested revision."
  }
  assert {
    condition     = aws_lambda_function.api.reserved_concurrent_executions == 2
    error_message = "The demo must cap concurrency."
  }
}

run "reject_production_example" {
  command = plan
  variables {
    environment = "production"
  }
  expect_failures = [var.environment]
}

run "reject_missing_owner" {
  command = plan
  variables {
    owner = " "
  }
  expect_failures = [var.owner]
}
