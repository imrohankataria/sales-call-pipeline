"""Pure Slack signature validation and explicit demo skill routing."""
import hashlib
import hmac
import re


def verify_signature(raw, headers, secret, now):
    try:
        timestamp = headers['x-slack-request-timestamp']
        if not secret or abs(now - int(timestamp)) > 300:
            return False
        expected = 'v0=' + hmac.new(secret.encode(), b'v0:' + timestamp.encode() + b':' + raw, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, headers.get('x-slack-signature', ''))
    except (KeyError, ValueError, TypeError):
        return False


def parse_command(form, team_id, allowed_users, grants=None):
    if not team_id or form.get('team_id') != team_id or form.get('user_id') not in allowed_users:
        raise ValueError('Workspace or user is not authorized for this demo')
    if form.get('command') != '/gtm':
        raise ValueError('Use /gtm')
    permitted = (grants or {}).get(form['user_id'], []) if grants is not None else ['call-review', 'meeting-prep']
    if form.get('text', '').strip() in ('skills', 'help', ''):
        return {'kind': 'skill_directory', 'permitted_skills': permitted, 'user_id': form['user_id']}
    head, separator, text = form.get('text', '').partition('|')
    words = head.strip().split()
    if len(words) != 2 or words[0] not in ('call-review', 'meeting-prep'):
        raise ValueError('Use /gtm call-review demo-001 | transcript, or /gtm meeting-prep demo-001')
    if words[0] not in permitted:
        raise ValueError('Your Slack identity is not authorized for that skill')
    if not re.fullmatch(r'demo-[A-Za-z0-9_-]{1,80}', words[1]):
        raise ValueError('Only synthetic opportunity IDs starting demo- are allowed')
    if words[0] == 'call-review' and (not separator or not 1 <= len(text.strip()) <= 10000):
        raise ValueError('Call review requires a transcript after |')
    trigger = form.get('trigger_id', '')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', trigger):
        raise ValueError('Invalid Slack request identifier')
    channel = form.get('channel_id', '')
    if not re.fullmatch(r'[A-Za-z0-9]{1,30}', channel):
        raise ValueError('Invalid Slack channel')
    return {'skill_id': words[0], 'input': text.strip(), 'opportunity_id': words[1],
            'request_id': 'slack-' + trigger.replace('.', '-'), 'channel_id': channel,
            'actor': {'team_id': team_id, 'user_id': form['user_id'], 'credential_mode': 'service_role'},
            'source': 'slack'}
