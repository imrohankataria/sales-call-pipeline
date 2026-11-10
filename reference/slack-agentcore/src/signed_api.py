"""SigV4 HTTP client; role credentials stay in the Python process."""
import json
import urllib.error
import urllib.request
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def call_api(session, base_url, path, body=None):
    if path not in ("/health", "/exercises", "/openapi.json", "/sales") and not (
        path.startswith("/exercises/P") and path[-2:].isdigit() and 1 <= int(path[-2:]) <= 30
    ):
        raise ValueError("Unknown API route")
    data = None if body is None else json.dumps(body, allow_nan=False).encode()
    url = base_url.rstrip("/") + path
    request = AWSRequest(method="GET" if data is None else "POST", url=url, data=data,
                         headers={"Content-Type": "application/json"})
    SigV4Auth(session.get_credentials().get_frozen_credentials(), "execute-api", session.region_name).add_auth(request)
    prepared = request.prepare()
    req = urllib.request.Request(url, data=data, headers=dict(prepared.headers), method=prepared.method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        result = json.loads(error.read())
        if error.code == 409:
            return result
        raise ValueError("API request failed: " + str(error.code) + " " + json.dumps(result)) from error
