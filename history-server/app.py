import os
import json
import datetime
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify

app = Flask(__name__)

GARAGE_BUCKET_NAME = "price-data"

# Initialize Boto3 S3 Client for Garage
s3_client = boto3.client(
    "s3",
    endpoint_url=os.environ.get('GARAGE_URI', 'http://garage:3900'),
    aws_access_key_id=os.environ.get('ACCESS_KEY'),
    aws_secret_access_key=os.environ.get('SECRET_KEY'),
    region_name="garage",
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)

def bucket_exists(bucket_name):
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError:
        return False

def push_data_to_garage(date, prices):
    if not bucket_exists(GARAGE_BUCKET_NAME):
        s3_client.create_bucket(Bucket=GARAGE_BUCKET_NAME)

    file_name = f"{date}.json"
    s3_client.put_object(
        Bucket=GARAGE_BUCKET_NAME,
        Key=file_name,
        Body=json.dumps(prices),
        ContentType="application/json"
    )

def get_prices_for_date(date):
    if not bucket_exists(GARAGE_BUCKET_NAME):
        return None, 404

    file_name = f"{date}.json"

    try:
        response = s3_client.get_object(Bucket=GARAGE_BUCKET_NAME, Key=file_name)
        price_data = json.loads(response['Body'].read().decode('utf-8'))
        return price_data, 200
    except ClientError as e:
        if e.response['Error']['Code'] in ['404', 'NoSuchKey']:
            return {"error": f"No price records found for date {date}"}, 404
        return {"error": str(e)}, 500

@app.route("/api/prices", methods=['GET'])
def get_prices():
    day = request.args.get("day")
    if not day:
        return jsonify({"error": "Query parameter 'day' is required"}), 400

    prices, status_code = get_prices_for_date(day)
    return jsonify(prices), status_code

@app.route("/api/prices", methods=['POST'])
def post_prices():
    day = request.args.get("day")
    if not day:
        return jsonify({"error": "Query parameter 'day' is required"}), 400

    prices = request.get_json()
    if not prices:
        return jsonify({"error": "Invalid JSON body"}), 400

    push_data_to_garage(day, prices)
    return jsonify({"message": "Upload of prices succeeded"}), 201

@app.route("/health", methods=['GET'])
def health():
    return "History Server is working properly!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
