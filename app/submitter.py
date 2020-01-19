#!/usr/bin/env python3

import json
import os
import urllib.parse
import boto3
from botocore.exceptions import ClientError
from datadog import initialize as datadog_init
from datadog import statsd as datadog_statsd


class CloudResourceHandler:
    """ Class that handles operations related to SQS and S3 resources """

    def __init__(self, sqs_queue_url, sqs_client, s3_client):
        if sqs_client is None or s3_client is None:
            print("Error: unable to initialize boto3, clients not found!")
            exit(1)
        self.sqs_queue_url = sqs_queue_url
        self.sqs_message_body = None
        self.receipt_handle = None
        self.s3_client = s3_client
        self.sqs_client = sqs_client

    def get_sqs_message(self):
        """ function that tries to read a single message from the SQS queue """

        try:
            return self.sqs_client.receive_message(QueueUrl=self.sqs_queue_url,
                                                   MaxNumberOfMessages=1,
                                                   WaitTimeSeconds=0,
                                                   VisibilityTimeout=15)
        except ClientError as ex:
            if ex.response['Error']['Code'] == 'AWS.SimpleQueueService.NonExistentQueue':
                print("SQS Queue does not exist! Terminating ...")
                exit(1)
            if ex.response['Error']['Code'] == 'InvalidAddress':
                print("SQS Queue URL is not valid! Terminating ...")
                exit(1)
            else:
                raise

    def has_available_messages(self):
        """ function to cache the next available message from the SQS queue """

        msg = self.get_sqs_message()
        if len(msg) > 1 and "Messages" in msg:
            self.receipt_handle = msg['Messages'][0]['ReceiptHandle']
            self.sqs_message_body = json.loads(msg['Messages'][0]['Body'])
            return True
        else:
            self.receipt_handle = None
            self.sqs_message_body = None
            return False

    def get_s3_bucket_name(self):
        """ returns the S3 bucket's name if there is a cached message """

        if self.sqs_message_body and "Records" in self.sqs_message_body:
            return self.sqs_message_body['Records'][0]['s3']['bucket']['name']
        else:
            return None

    def s3_key_is_valid(self):
        """ validates cached s3 key, expects: 'date=????????/metrics.json' """

        if self.get_s3_key() == "" or self.get_s3_key() is None:
            return False
        else:
            parts = self.get_s3_key().split('/')
            if "date=" not in parts[0] or ".json" not in parts[1]:
                return False
            return True

    def get_s3_key(self):
        """ returns the S3 key if there is a cached message """

        if self.sqs_message_body and "Records" in self.sqs_message_body:
            return urllib.parse.unquote(self.sqs_message_body['Records'][0]['s3']['object']['key'])
        else:
            return None

    def get_s3_data(self):
        """ if there is cached message, tries to download file from S3 """

        if self.sqs_message_body:
            s3_key = self.get_s3_key()
            s3_bucket_name = self.get_s3_bucket_name()
            if s3_key and s3_bucket_name:
                try:
                    raw_s3_file = self.s3_client.get_object(Bucket=s3_bucket_name, Key=s3_key)
                except ClientError as ex:
                    if ex.response['Error']['Code'] == 'NoSuchKey':
                        print("Error: file does not exist in S3!")
                        return None
                    else:
                        raise
                if raw_s3_file:
                    return json.loads(raw_s3_file["Body"].read().decode('utf-8'))
                else:
                    print("Error: raw file could not be fetched!")
                    return None
            else:
                print("Error: s3_key and s3_bucket_name could not be determined from sqs message!")
                return None
        else:
            print("Error: sqs message body not found!")
            return None

    def remove_cached_message(self):
        """ deletes cached message from SQS via saved receipt_handle """

        if self.receipt_handle:
            print(" - removing message from SQS ({}...)".format(self.receipt_handle[:25]))
            self.sqs_client.delete_message(QueueUrl=self.sqs_queue_url, ReceiptHandle=self.receipt_handle)
            self.receipt_handle = None
            self.sqs_message_body = None


class MetricSubmitter:
    """ class to send metrics to DataDog by using the CloudResourceHandler class"""

    def __init__(self, statsd=datadog_statsd, sqs_client=None, s3_client=None):
        """ Initializes datadog so statsd knows how to send data to DataDog """

        if not os.environ.get('SQS_QUEUE_URL'):
            print("Error: ENVIRONMENT variable 'SQS_QUEUE_URL' not set! Exiting ...")
            exit(1)
        datadog_init(**{
            'statsd_host': os.environ.get('STATSD_HOST') or 'datadog-agent',
            'statsd_port': os.environ.get('STATSD_PORT') or 8125
        })

        print("Initializing new AWS handler class with SQS URL - {}".format(os.environ.get('SQS_QUEUE_URL')))
        self.aws_handler = CloudResourceHandler(os.environ.get('SQS_QUEUE_URL'),
                                                sqs_client,
                                                s3_client)
        self.ddg_statsd = statsd

    def datadog_submit(self, metrics):
        """ Submission to DataDog via local datadog-agent, assumes following JSON data format:
            { "job_success" : 1, "job_result"  : 12345 }
        """

        tags = ['cloud_job_metric']
        if "job_success" in metrics and metrics["job_success"] == 1:
            self.ddg_statsd.event('Job Success!',
                                  'Cloud process completed successfully.',
                                  alert_type='success',
                                  tags=tags)
            for key, value in metrics.items():
                if key != "job_success":
                    self.ddg_statsd.gauge(key, value, tags=tags)
        else:
            self.ddg_statsd.event('Job Failure!',
                                  'Cloud process encountered a failure!',
                                  alert_type='error',
                                  tags=tags)

    def run(self):
        """ main routine collecting metrics from AWS and submitting them to DataDog """

        print("Processing available messages in SQS queue:")
        while self.aws_handler.has_available_messages():
            if "Event" in self.aws_handler.sqs_message_body and self.aws_handler.sqs_message_body["Event"] == "s3:TestEvent":
                print(" - found S3 TestEvent in queue, skip & delete message.")
                self.aws_handler.remove_cached_message()
                continue

            if not self.aws_handler.s3_key_is_valid():
                print(" - S3 key ({}) is invalid, skip & delete message.".format(self.aws_handler.get_s3_key()))
                self.aws_handler.remove_cached_message()
                continue

            metrics = self.aws_handler.get_s3_data()
            if not metrics:
                print(" - no data in s3 file: '{}', skip & delete message.".format(self.aws_handler.get_s3_key()))
                self.aws_handler.remove_cached_message()
                continue

            print(" - sending data to DataDog via statsd/datadog-agent.")
            self.datadog_submit(metrics)
            self.aws_handler.remove_cached_message()

        print("No more messages visible in the queue, shutting down ...")


def main():
    # set ENV var to talk to datadog-agent running locally in a docker container
    os.environ['STATSD_HOST'] = '0.0.0.0'

    # set ENV var to be the SQS URL reported by the terraform apply output
    os.environ['SQS_QUEUE_URL'] = 'https://sqs.eu-central-1.amazonaws.com/546454927816/cloud-job-results-queue'

    # create boto3 session with credentials from local profile
    session = boto3.Session(profile_name='personal-aws')

    # run the app that submits data from S3 to DataDog
    submitter = MetricSubmitter(statsd=datadog_statsd,
                                sqs_client=session.client('sqs'),
                                s3_client=session.client('s3'))
    submitter.run()

    #TODO: make Dockerfile for main python script


if __name__ == '__main__':
    main()
