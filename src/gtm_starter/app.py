"""HTTP entrypoint hosted by AgentCore Runtime; no persistent local CRM in cloud."""

import json
import os
import time

from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext
from .cloud import BedrockProposer, GatewayCRM, ServiceError, validate_gateway_url
from .core import Catalog, Workflow

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    start = time.monotonic()
    region = os.environ.get('AWS_REGION', 'us-east-2')
    enabled = [name.strip() for name in os.environ.get('GTM_ENABLED_SKILLS', 'call-review,meeting-prep').split(',') if name.strip()]
    try:
        catalog = Catalog.default()
        if not set(enabled).issubset(catalog.entries):
            raise ServiceError('invalid_configuration')
        workflow = Workflow(catalog, None, enabled_skills=enabled)
        skill, _, _ = workflow.validate_request(payload)
        if skill == 'skills':
            return {**workflow.run(payload), 'identity_mode': 'AWS_IAM_service_role'}
        try:
            gateway = validate_gateway_url(os.environ.get('GATEWAY_URL'), region)
            max_tokens = int(os.environ.get('GTM_MAX_TOKENS', '512'))
            if not 1 <= max_tokens <= 4096:
                raise ValueError('invalid_max_tokens')
        except (ValueError, TypeError) as exc:
            raise ServiceError('invalid_configuration') from exc
        workflow.crm = GatewayCRM(gateway, region, os.environ.get('GATEWAY_TARGET', 'crm'), BedrockAgentCoreContext.get_workload_access_token())
        if skill == 'call-review':
            workflow.proposer = BedrockProposer(region, os.environ.get('GTM_MODEL_ID', 'amazon.nova-lite-v1:0'), max_tokens, request_id=payload['request_id'])
        result = workflow.run(payload)
        print(json.dumps({'event': 'workflow_completed', 'skill': result['skill'], 'version': result['version'], 'request_id': result.get('request_id'), 'duration_ms': round((time.monotonic() - start) * 1000)}))
        return result
    except ValueError as exc:
        return {'status': 'rejected', 'reason': str(exc)}
    except ServiceError as exc:
        print(json.dumps({'event': 'workflow_failed', 'reason': str(exc), 'duration_ms': round((time.monotonic() - start) * 1000)}))
        return {'status': 'failed', 'reason': str(exc)}
    except Exception as exc:
        print(json.dumps({'event': 'workflow_failed', 'reason': 'internal_error', 'error_type': type(exc).__name__}))
        return {'status': 'failed', 'reason': 'internal_error'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
