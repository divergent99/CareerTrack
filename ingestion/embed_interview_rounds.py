import os
import json
import boto3
from db import get_conn
from dotenv import load_dotenv

load_dotenv()

bedrock = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1",
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
)

def get_embedding(text):
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        body=json.dumps({"inputText": text, "dimensions": 1024}),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]

def backfill():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, questions_asked FROM interview_rounds 
        WHERE questions_asked IS NOT NULL 
        AND questions_asked != '' 
        AND questions_embedding IS NULL
    """)
    rows = cur.fetchall()

    print(f"Found {len(rows)} rounds to embed")

    for round_id, questions in rows:
        embedding = get_embedding(questions)
        cur.execute(
            "UPDATE interview_rounds SET questions_embedding = %s WHERE id = %s",
            (embedding, round_id)
        )
        conn.commit()
        print(f"Embedded round {round_id}: {questions[:60]}...")

    cur.close()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    backfill()