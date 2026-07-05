# test_bedrock_embeddings.py
import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv()

client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)

def get_embedding(text):
    response = client.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text, "dimensions": 1024}),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]

if __name__ == "__main__":
    text = "Tell me about a time you optimized a RAG pipeline for latency."
    embedding = get_embedding(text)
    print(f"Embedding length: {len(embedding)}")
    print(f"First 5 values: {embedding[:5]}")