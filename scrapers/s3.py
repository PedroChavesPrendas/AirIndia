from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError
from urllib import parse
import os
from dotenv import load_dotenv
load_dotenv()
import sys
# sys.path.append('../utils')

from utils.log import get_logger

logger = get_logger()

AWS_ACCESS = os.getenv('AWS_ACCESS')
AWS_SECRET = os.getenv('AWS_SECRET')
AWS_REGION = os.getenv('AWS_REGION')
DEST_AWS_BUCKET_NAME = os.getenv('DEST_AWS_BUCKET_NAME')

def upload_s3(local_file, s3_file, airline):
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS,
                          aws_secret_access_key=AWS_SECRET, region_name=AWS_REGION)

    try:
        bucket_name = DEST_AWS_BUCKET_NAME
        key = f"v0/WebScraping/{airline}/{s3_file}"
        s3_url= f"https://{bucket_name}.s3.amazonaws.com/{key}"
        tags = {
                "airline_name": airline,
                }
        s3.upload_file(local_file,
                       bucket_name,
                       Key=key,
                       ExtraArgs={"Tagging": parse.urlencode(tags)}
                       )
        logger.info(f"uploaded {s3_file} to S3 for {airline}")
        return True, s3_url
    except FileNotFoundError:
        return False, []
    except NoCredentialsError:
        return False, []