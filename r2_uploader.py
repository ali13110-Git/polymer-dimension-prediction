import os
import boto3
from botocore.config import Config
from dotenv import load_dotenv

# Load secrets from.env
load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
ACCESS_KEY = os.getenv("CLOUDFLARE_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("CLOUDFLARE_SECRET_ACCESS_KEY")
BUCKET_NAME = os.getenv("R2_BUCKET_NAME")


# The S3-compatible endpoint for Cloudflare R2
endpoint_url = f"https://905183619d72e2fcdbb6d255ab5ce5c2.r2.cloudflarestorage.com"

def upload_to_r2(file_path, object_name):
    s3 = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version='s3v4')
    )
    
    try:
        s3.upload_file(file_path, BUCKET_NAME, object_name)
        print(f"✅ Success: {object_name} uploaded to {BUCKET_NAME}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")

if __name__ == "__main__":
    # Test with the dummy file you created earlier
    upload_to_r2("test_report.pdf", "test_report.pdf")

    print(f"🚀 Starting test upload for {TEST_FILE}...")
    upload_to_r2(TEST_FILE, TEST_FILE)
