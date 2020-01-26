# Python in the Cloud

[![Build Status](https://travis-ci.org/florianakos/python-testing.svg?branch=master)](https://travis-ci.org/florianakos/python-testing)

This is a proof of concept project in which I integrate AWS and DataDog to monitor and track the result of certain workloads running in the cloud.

Technology stack:

* `python 3`: language for main service
* `localstack`: for testing without real AWS resources
* `docker`: packaging the main executable
* `docker-compose`: packaging integration tests
* `travis-CI`: for automating integration tests
* `aws s3/sqs`: for storing files and queueing messages
* `datadog`: to display metrics and generate alerts

To read more about the contents of this repo, read my blog post at: [link](https://flrnks.netlify.com/post/python-aws-datadog-testing/)