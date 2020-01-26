# Python in the cloud project

[![Build Status](https://travis-ci.org/florianakos/python-testing.svg?branch=master)](https://travis-ci.org/florianakos/python-testing)

This is a proof of concept project in which I integrate AWS and DataDog services into a service which tracks the result of certain cloud workloads and forwards metrics about them from AWS to DataDog for display and alerting.

Technology stack:

* `python 3`: language for main service
* `localstack`: for testing without real AWS resources
* `docker`: packaging the main executable
* `docker-compose`: packaging integration tests
* `travis-CI`: for automating integration tests
* `aws s3/sqs`: for storing file and queueing messages
* `datadog`: to display metrics and generate alerts

To read more about the contents of this repo, read my blog post at: [link](https://flrnks.netlify.com/post/python-aws-datadog-testing/)