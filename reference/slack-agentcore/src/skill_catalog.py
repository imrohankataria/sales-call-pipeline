"""Load only an immutable release's approved and content-verified skills."""
import hashlib
import re

KNOWN_TOOLS = {'crm-tools___commit_sales', 'crm-tools___filter_findings', 'crm-tools___get_opportunity'}


def load_skill(skill_id, catalog, read_object):
    try:
        item = catalog['skills'][skill_id]
    except (KeyError, TypeError) as error:
        raise ValueError('Unknown skill in pinned catalog') from error
    version = item['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+', version) or not re.fullmatch(r'[a-z-]+', skill_id):
        raise ValueError('Invalid skill identity')
    if item['key'] != f'skills/{skill_id}/{version}/SKILL.md':
        raise ValueError('Skill path does not match pinned version')
    tools = item['allowed_tools']
    if not isinstance(tools, list) or not set(tools).issubset(KNOWN_TOOLS):
        raise ValueError('Skill requests unapproved tools')
    raw = read_object(item['key'])
    if len(raw) > 20000 or hashlib.sha256(raw).hexdigest() != item['sha256']:
        raise ValueError('Skill content hash mismatch')
    return {**item, 'instructions': raw.decode('utf-8'), 'release': catalog['release']}
