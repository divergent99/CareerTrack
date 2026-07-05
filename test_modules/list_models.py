# list_bedrock_models.py
import os
import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "bedrock",
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)

response = client.list_foundation_models()
for model in response["modelSummaries"]:
    if "embed" in model["modelId"].lower():
        print(model["modelId"], "-", model.get("modelName"))