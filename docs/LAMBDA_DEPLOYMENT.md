# Deploy Bid Generator API to AWS Lambda with Mangum

This guide deploys the FastAPI app to AWS Lambda as a Python `.zip` package using `Mangum`.

## Important Streaming Note

The API endpoint below currently uses `StreamingResponse`:

```text
POST /api/v1/jobs/generate-bid
```

With `Mangum`, Lambda/API Gateway normally buffers the ASGI response instead of delivering token-by-token SSE chunks in real time. The endpoint can still work, but clients may receive the response after generation completes rather than as live streaming chunks.

If true live SSE streaming becomes a hard requirement later, use Lambda Web Adapter or run the app on ECS/App Runner/EC2. For your request here, this guide uses Mangum only.

## What You Will Create

- One Lambda function using the Python runtime.
- One Lambda Function URL for HTTPS access.
- One zip deployment package containing your app and dependencies.
- Environment variables for Mistral and Supabase.

## Files Added for Lambda

The Lambda handler is:

```text
lambda_handler.handler
```

It points to:

```python
from mangum import Mangum
from main import app

handler = Mangum(app, lifespan="on")
```

## Prerequisites

Install and configure these:

```bash
aws --version
python3 --version
zip --version
aws configure
```

You also need:

- Supabase schema already created from `sql/supabase_schema.sql`.
- Supabase Postgres connection string, preferably the pooler URL.
- Mistral API key.
- AWS permissions for IAM, Lambda, CloudWatch Logs, and Function URLs.

## 1. Choose Names

```bash
export AWS_REGION=us-east-1
export FUNCTION_NAME=bid-generator-api
export ROLE_NAME=bid-generator-lambda-role
export ZIP_FILE=bid-generator-lambda.zip
```

## 2. Test Locally First

From the project root:

```bash
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
curl -sS http://127.0.0.1:8000/health
```

Expected:

```json
{"status":"ok"}
```

Stop the server with `Ctrl+C`.

## 3. Create the Lambda Execution Role

Create a trust policy:

```bash
cat > /tmp/lambda-trust-policy.json <<'JSON'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
JSON
```

Create the role:

```bash
aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document file:///tmp/lambda-trust-policy.json
```

Attach CloudWatch Logs permission:

```bash
aws iam attach-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Export the role ARN:

```bash
export LAMBDA_ROLE_ARN=$(aws iam get-role \
  --role-name "$ROLE_NAME" \
  --query 'Role.Arn' \
  --output text)
echo "$LAMBDA_ROLE_ARN"
```

Wait 10-20 seconds before creating the function. IAM role propagation can lag.

## 4. Build the Zip Package

Use a clean build directory:

```bash
rm -rf build "$ZIP_FILE"
mkdir -p build
```

Install dependencies into `build/`:

```bash
python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --target build \
  --implementation cp \
  --python-version 312 \
  --only-binary=:all: \
  --upgrade \
  -r requirements.txt
```

Copy your source code:

```bash
cp -r app build/app
cp main.py lambda_handler.py build/
```

Create the zip:

```bash
cd build
zip -r "../$ZIP_FILE" .
cd ..
```

Check size:

```bash
ls -lh "$ZIP_FILE"
```

AWS Lambda zip packages have size limits. If direct upload is too large, upload the zip to S3 first and create/update Lambda from S3.

## 5. Create the Lambda Function

```bash
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.12 \
  --handler lambda_handler.handler \
  --role "$LAMBDA_ROLE_ARN" \
  --zip-file "fileb://$ZIP_FILE" \
  --architectures x86_64 \
  --timeout 120 \
  --memory-size 1024 \
  --region "$AWS_REGION"
```

Wait until active:

```bash
aws lambda wait function-active \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

## 6. Add Environment Variables

Do not put `.env` inside the zip. Set Lambda environment variables instead.

```bash
aws lambda update-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --environment "Variables={
MISTRAL_API_KEY=replace_me,
SUPABASE_URL=https://your-project-ref.supabase.co,
SUPABASE_DB_URL=postgresql://postgres.your-project-ref:replace_me@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require,
DEBUG=production,
RAG_TOP_K=3,
MISTRAL_CHAT_MODEL=mistral-small-latest,
MISTRAL_EMBED_MODEL=mistral-embed
}"
```

Recommended Supabase DB URL for Lambda:

```text
postgresql://postgres.<project-ref>:<db-password>@aws-0-<region>.pooler.supabase.com:6543/postgres?sslmode=require
```

Use the Supabase pooler connection string from:

```text
Supabase Dashboard -> Project Settings -> Database -> Connection string
```

Lambda can scale into many concurrent execution environments, so the pooler is safer than connecting directly to the database host.

Wait for the update:

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

## 7. Create a Lambda Function URL

For simple public HTTPS access:

```bash
aws lambda create-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --auth-type NONE \
  --cors '{
    "AllowOrigins": ["*"],
    "AllowMethods": ["GET", "POST", "OPTIONS"],
    "AllowHeaders": ["content-type"],
    "MaxAge": 86400
  }' \
  --region "$AWS_REGION"
```

Get the URL:

```bash
export FUNCTION_URL=$(aws lambda get-function-url-config \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION" \
  --query FunctionUrl \
  --output text)
echo "$FUNCTION_URL"
```

## 8. Test the Deployed API

Health:

```bash
curl -sS "$FUNCTION_URL/health"
```

List jobs:

```bash
curl -sS "$FUNCTION_URL/api/v1/jobs/?limit=5"
```

Seed a bid:

```bash
curl -sS -X POST "$FUNCTION_URL/api/v1/bids/seed" \
  -H 'Content-Type: application/json' \
  --data '{
    "title": "Build a FastAPI dashboard",
    "description": "Create a FastAPI backend with Supabase persistence.",
    "budget": "$500",
    "skills": ["FastAPI", "Supabase", "PostgreSQL"],
    "client_info": {
      "country": "United States",
      "hire_rate": "80%",
      "reviews": 4.9,
      "total_spent": "$20k+"
    },
    "bid_text": "I can help you build a clean FastAPI backend with Supabase persistence, validation, and practical API structure."
  }'
```

Generate a bid:

```bash
curl -sS -X POST "$FUNCTION_URL/api/v1/jobs/generate-bid" \
  -H 'Content-Type: application/json' \
  --data '{
    "title": "Create a Supabase-backed FastAPI API",
    "description": "I need an API that stores jobs, creates proposals with AI, and retrieves past proposals for context.",
    "budget": "$750",
    "skills": ["FastAPI", "Supabase", "PostgreSQL", "AI integration"],
    "client_info": {
      "country": "United States",
      "hire_rate": "90%",
      "reviews": 5,
      "total_spent": "$50k+"
    }
  }'
```

With Mangum this may arrive as a buffered response instead of live chunks.

## 9. View Logs

```bash
aws logs tail "/aws/lambda/$FUNCTION_NAME" \
  --follow \
  --region "$AWS_REGION"
```

Useful checks:

```bash
aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"

aws lambda get-function-configuration \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

## 10. Deploy Updates Later

Rebuild the zip:

```bash
rm -rf build "$ZIP_FILE"
mkdir -p build

python3 -m pip install \
  --platform manylinux2014_x86_64 \
  --target build \
  --implementation cp \
  --python-version 312 \
  --only-binary=:all: \
  --upgrade \
  -r requirements.txt

cp -r app build/app
cp main.py lambda_handler.py build/

cd build
zip -r "../$ZIP_FILE" .
cd ..
```

Update Lambda:

```bash
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://$ZIP_FILE" \
  --region "$AWS_REGION"
```

Wait:

```bash
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$AWS_REGION"
```

## 11. If the Zip Is Too Large

Upload it to S3:

```bash
export DEPLOY_BUCKET=your-existing-bucket-name
aws s3 cp "$ZIP_FILE" "s3://$DEPLOY_BUCKET/$ZIP_FILE" --region "$AWS_REGION"
```

Create from S3:

```bash
aws lambda create-function \
  --function-name "$FUNCTION_NAME" \
  --runtime python3.12 \
  --handler lambda_handler.handler \
  --role "$LAMBDA_ROLE_ARN" \
  --code S3Bucket="$DEPLOY_BUCKET",S3Key="$ZIP_FILE" \
  --architectures x86_64 \
  --timeout 120 \
  --memory-size 1024 \
  --region "$AWS_REGION"
```

Update from S3:

```bash
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --s3-bucket "$DEPLOY_BUCKET" \
  --s3-key "$ZIP_FILE" \
  --region "$AWS_REGION"
```

## 12. Production Notes

- Do not commit `.env`.
- Use Supabase pooler URLs for Lambda.
- URL-encode special characters in the Supabase DB password.
- Keep `DEBUG=production` or `DEBUG=false`.
- Start with 1024 MB memory and 120 seconds timeout.
- If the Function URL is public, add auth or rate limiting before real production use.
- For live streaming responses, Mangum is not the ideal deployment target.

## Troubleshooting

### `Unable to import module 'lambda_handler'`

Make sure `lambda_handler.py` is at the root of the zip:

```bash
unzip -l "$ZIP_FILE" | grep lambda_handler.py
```

### `No module named mangum`

Rebuild the zip after adding `mangum`:

```bash
python3 -m pip install --target build -r requirements.txt
```

### Supabase Connection Fails

Check:

- `SUPABASE_DB_URL` is set in Lambda.
- Password is URL-encoded.
- You are using the pooler host, not only `https://project.supabase.co`.
- `vector` extension and tables exist.

### Mistral Calls Fail

Check:

- `MISTRAL_API_KEY` is set in Lambda.
- Lambda has outbound internet access. If you attach Lambda to a private VPC, you need NAT for calls to Mistral and Supabase.

### Response Looks Buffered

That is expected with Mangum for the streaming endpoint. The endpoint can still complete and persist the generated bid, but real-time SSE chunks may not reach the client one by one.
