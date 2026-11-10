import json
import os
import boto3
from botocore.config import Config
from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext
from agent_logic import run_sales_agent
from signed_api import call_api
from skill_catalog import load_skill
from gtm_logic import run_gtm
from gateway_client import call_tool

app = BedrockAgentCoreApp()
session = boto3.Session(region_name=os.environ.get("AWS_REGION", "us-east-2"))
model = session.client("bedrock-runtime", config=Config(connect_timeout=5, read_timeout=35, retries={"total_max_attempts": 1}))


@app.entrypoint
def invoke(payload, context):
    try:
        if isinstance(payload, dict) and 'skill_id' in payload:
            s3 = session.client('s3')
            bucket = os.environ['SKILL_BUCKET']
            def read(key):
                return s3.get_object(Bucket=bucket, Key=key, ExpectedBucketOwner=os.environ['AWS_ACCOUNT_ID'])['Body'].read()
            catalog = json.loads(read(os.environ['SKILL_CATALOG_KEY']))
            result = run_gtm(payload, model, lambda name: load_skill(name, catalog, read),
                             lambda name, args: call_tool(session, os.environ['GATEWAY_URL'], name, args))
            result['workload_identity_token_present'] = bool(BedrockAgentCoreContext.get_workload_access_token())
        else:
            result = run_sales_agent(payload, model, lambda path, body: call_api(session, os.environ["EXERCISE_API_URL"], path, body))
        print(json.dumps({"event": "agent_completed", "status": result["status"], "model_calls": result["model_calls"],
                          "latency_ms": result["latency_ms"], "usage": result["usage"],
                          'request_id': payload.get('request_id'), 'skill_id': result.get('skill_id'),
                          'skill_version': result.get('skill_version'), 'catalog_release': result.get('catalog_release'),
                          'tool_trace': result.get('tool_trace')}))
        return result
    except ValueError as error:
        return {"status": "invalid_request", "message": str(error)}
    except Exception as error:
        print(json.dumps({"event": "agent_error", "error_type": type(error).__name__}))
        return {"status": "error", "error_type": type(error).__name__}


if __name__ == "__main__":
    app.run()
