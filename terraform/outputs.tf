output "queue_url" {
  value = aws_sqs_queue.message_queue.id
}

output "bucket_name"{
  value = aws_s3_bucket.ddg_aws_bucket.id
}