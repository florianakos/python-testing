provider "aws" {
  region = var.region
  profile = "personal-aws"
}

resource "aws_iam_role" "aws_lambda_s3_role" {
  name               = "LambdaRole"
  description        = "Role that allowed to be assumed by AWS Lambda, which will be taking all actions."
  tags = {
      owner = "TheBoss"
  }
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "basic-exec-role" {
  role       = aws_iam_role.aws_lambda_s3_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "s3_lambda_access" {
  name   = "lambda_s3_access"
  path   = "/"
  policy = data.aws_iam_policy_document.s3_lambda_access.json
}

data "aws_iam_policy_document" "s3_lambda_access" {
  statement {
    effect    = "Allow"
    resources = ["arn:aws:s3:::${var.bucket_name}/*"]
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:ListBucket",
    ]
  }
}

resource "aws_iam_role_policy_attachment" "s3_lambda_access" {
  role       = aws_iam_role.aws_lambda_s3_role.name
  policy_arn = aws_iam_policy.s3_lambda_access.id
}

resource "aws_lambda_function" "lambda_mock_datasource" {
  role             = aws_iam_role.aws_lambda_s3_role.arn
  handler          = "mock_data_source.handler"
  runtime          = "python3.6"
  filename         = "mock_data_source.zip"
  function_name    = "mock_data_source"
  source_code_hash = base64sha256(filebase64("../app/lambda/mock_data_source.zip"))
}

resource "aws_lambda_permission" "allow_cloudwatch_events_call" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_mock_datasource.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.mock_data_generate_schedule.arn
}

resource "aws_cloudwatch_event_rule" "mock_data_generate_schedule" {
  name                = "mock_data_generate_schedule"
  description         = "Periodic call to AWS Lambda function"
  schedule_expression = "cron(0/1 * * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda_target_details" {
  arn       = aws_lambda_function.lambda_mock_datasource.arn
  rule      = aws_cloudwatch_event_rule.mock_data_generate_schedule.name
  target_id = "AWSLambdaFuncMockDataSource"
}

resource "aws_sqs_queue" "message_queue" {
  name                      = var.queue_name
  delay_seconds             = 0
  max_message_size          = 2048
  message_retention_seconds = 86400
  receive_wait_time_seconds = 0
  tags = {
    Owner = "CloudAdmin"
    Project = "DataDog-AWS-Integration"
  }
}

resource "aws_sqs_queue_policy" "sqs_policy" {
  queue_url = aws_sqs_queue.message_queue.id
  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Id": "sqspolicy",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.message_queue.arn}",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "${aws_s3_bucket.ddg_aws_bucket.arn}"
        }
      }
    }
  ]
}
POLICY
}

resource "aws_s3_bucket" "ddg_aws_bucket" {
  bucket = var.bucket_name
  tags = {
    Name        = "My bucket for DataDog AWS integration proejct..."
    Environment = "Dev"
  }
  force_destroy = "true"
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.ddg_aws_bucket.id
  queue {
    queue_arn     = aws_sqs_queue.message_queue.arn
    events        = ["s3:ObjectCreated:*"]
    filter_suffix = ".json"
  }
}
