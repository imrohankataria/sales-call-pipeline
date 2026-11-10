"""Short-lived application authorization, distinct from AWS/OAuth credentials."""
import hashlib
import hmac
import json
import functools
import os


def sign_grant(grant, secret):
    raw = json.dumps(grant, sort_keys=True, separators=(',', ':')).encode()
    return {'grant': grant, 'signature': hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()}


def verify_grant(auth, secret, tool, args, now):
    try:
        grant = auth['grant']
        expected = sign_grant(grant, secret)['signature']
        if not hmac.compare_digest(expected, auth['signature']) or grant['expires_at'] < now:
            return False
        if 'crm-tools___' + tool not in grant['allowed_tools']:
            return False
        if 'opportunity_id' in args and args['opportunity_id'] != grant['opportunity_id']:
            return False
        if 'request_id' in args and args['request_id'] != grant['request_id']:
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


@functools.lru_cache(maxsize=1)
def execution_secret():
    import boto3
    return json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=os.environ['AUTH_SECRET_ARN'])['SecretString'])['secret']
