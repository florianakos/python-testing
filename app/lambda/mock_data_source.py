from random import randint
import boto3
import json
from datetime import date

def handler(event, context):
    s3_client = boto3.resource('s3')
    s3_client.Bucket('cloud-job-results-bucket')\
             .put_object(Key='date=' + date.today().strftime('%Y%m%d') + '/metrics.json',
                         Body=json.dumps({
                                       "job_success": True,
                                       "job_result":  randint(0, 1000)
                                  }))
    print("New file uploaded to s3 bucket...")
