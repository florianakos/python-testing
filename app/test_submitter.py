import unittest
import json
import os
from app.submitter import MetricSubmitter
from app.utils.datadog_fake_statsd import DataDogStatsDHelper
from app.utils.localstack_helper import LocalStackHelper


class TestGMMonitoringService(unittest.TestCase):
    """ Class for testing AWSHandler and DataDogSubmitterApp script using:
        - DataDogStatsDHelper for asserting on statsd submissions
        - LocalStackHelper for setting up AWS-like infrastructure locally """

    ls = None

    @classmethod
    def setUpClass(cls):
        """ method used to set up localstack before tests are run """
        print("\nSetting up test class parameters:")
        cls.s3_bucket_name = 'cloud-job-results-bucket'
        cls.sqs_queue_name = 'cloud-job-results-queue'
        cls.sqs_queue_url = "http://localstack:4576/queue/" + cls.sqs_queue_name
        cls.s3_payload = b'{"job_success": 1, "job_result": 123}'
        cls.s3_payload_invalid = b'{"job_success": 0}'

        print(" + waiting for Localstack to start in neighbor container!")
        cls.ls = LocalStackHelper(sqs_queue_name=cls.sqs_queue_name, s3_bucket_name=cls.s3_bucket_name)

        print(" + setting up infrastructure in localstack for integration tests!")
        cls.ls.get_s3_client().create_bucket(Bucket=cls.s3_bucket_name)
        cls.ls.get_sqs_client().create_queue(QueueName=cls.sqs_queue_name)
        cls.ls.session.resource("s3") \
                      .BucketNotification(cls.s3_bucket_name) \
                      .put(NotificationConfiguration={
                                'QueueConfigurations': [{
                                    'QueueArn': "arn:aws:sqs:us-east-1:000000000000:cloud-job-results-queue",
                                    'Events': ["s3:ObjectCreated:*"]
                                }]}
                          )
        cls.statsd_helper = DataDogStatsDHelper()
        os.environ['SQS_QUEUE_URL'] = cls.sqs_queue_url
        cls.submitter = MetricSubmitter(statsd=cls.statsd_helper,
                                        sqs_client=cls.ls.get_sqs_client(),
                                        s3_client=cls.ls.get_s3_client())

    def setUp(self):
        """ Purge the SQS queue and clean-up the DDG statsd handler class before each test """
        print("\nClean-up before each unit test!")
        self.ls.get_sqs_client().purge_queue(QueueUrl=self.sqs_queue_url)
        self.statsd_helper.reset()

    def test_ddg_submitter_valid_payload(self):
        """ Testing DataDog Statsd handler with S3 file with valid metrics """
        self.ls.get_s3_client().put_object(Bucket=self.s3_bucket_name,
                                           Key='date=20200112/metrics.json',
                                           Body=self.s3_payload)
        self.submitter.run()
        assert self.statsd_helper.event_alert_type == 'success'
        assert self.statsd_helper.event_counter == 1
        assert self.statsd_helper.event_title == 'Job Success!'
        assert self.statsd_helper.event_text == 'Cloud process completed successfully.'
        assert self.statsd_helper.event_tags == ['cloud_job_metric']
        assert self.statsd_helper.gauge_metric_name == "job_result"
        assert self.statsd_helper.gauge_metric_value == 123
        assert self.statsd_helper.gauge_tags == ['cloud_job_metric']
        assert self.statsd_helper.gauge_counter == 1

    def test_ddg_submitter_invalid_payload(self):
        """ Testing DataDog Statsd handler with S3 file with INVALID metrics """
        self.ls.get_s3_client().put_object(Bucket=self.s3_bucket_name,
                                           Key='date=20200112/metrics.json',
                                           Body=self.s3_payload_invalid)
        self.submitter.run()
        assert self.statsd_helper.event_alert_type == 'error'
        assert self.statsd_helper.event_counter == 1
        assert self.statsd_helper.event_title == 'Job Failure!'
        assert self.statsd_helper.event_text == 'Cloud process encountered a failure!'
        assert self.statsd_helper.event_tags == ['cloud_job_metric']
        assert self.statsd_helper.gauge_metric_name is None
        assert self.statsd_helper.gauge_metric_value is None
        assert self.statsd_helper.gauge_tags is None
        assert self.statsd_helper.gauge_counter == 0

    def test_aws_handler_invalid_s3key(self):
        """ Test AWSHandler with file submitted with INVALID s3 key """
        print("Asserting AWSHandler functioning via test message sent to SQS:")
        self.assertFalse(self.submitter.aws_handler.has_available_messages())
        self.ls.get_s3_client().put_object(Bucket=self.s3_bucket_name,
                                           Key='test.json',
                                           Body=self.s3_payload)
        self.assertTrue(self.submitter.aws_handler.has_available_messages())
        self.assertEqual(self.submitter.aws_handler.get_s3_key(), 'test.json')
        self.assertEqual(self.submitter.aws_handler.get_s3_bucket_name(), self.s3_bucket_name)
        self.assertFalse(self.submitter.aws_handler.s3_key_is_valid())
        self.assertEqual(self.s3_payload.decode("utf-8"),
                         json.dumps(self.submitter.aws_handler.get_s3_data()))
        self.submitter.aws_handler.remove_cached_message()
        self.assertFalse(self.submitter.aws_handler.has_available_messages())

    def test_aws_handler_valid_s3key(self):
        """ Test AWSHandler with file submitted with VALID s3 key """
        print("Asserting AWSHandler functioning via test message sent to SQS:")
        self.assertFalse(self.submitter.aws_handler.has_available_messages())
        self.ls.get_s3_client().put_object(Bucket=self.s3_bucket_name,
                                           Key='date=20200112/metrics.json',
                                           Body=self.s3_payload)
        self.assertTrue(self.submitter.aws_handler.has_available_messages())
        self.assertEqual(self.submitter.aws_handler.get_s3_key(), 'date=20200112/metrics.json')
        self.assertEqual(self.submitter.aws_handler.get_s3_bucket_name(), self.s3_bucket_name)
        self.assertTrue(self.submitter.aws_handler.s3_key_is_valid())
        self.assertEqual(self.s3_payload.decode("utf-8"),
                         json.dumps(self.submitter.aws_handler.get_s3_data()))
        self.submitter.aws_handler.remove_cached_message()
        self.assertTrue(self.submitter.aws_handler.has_available_messages())


if __name__ == '__main__':
    unittest.main()
