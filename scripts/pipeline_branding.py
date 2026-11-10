"""Public project attribution; never used for authorization or routing."""

WEBSITE = 'https://deploy.rohankataria.com'
ATTRIBUTION = {'Author': 'Rohan Kataria', 'Website': WEBSITE}

# Tag shapes verified against the CloudFormation resource schemas in us-east-2.
MAP_TAGS = {'AWS::ApiGatewayV2::Api', 'AWS::ApiGatewayV2::Stage',
    'AWS::BedrockAgentCore::Gateway', 'AWS::BedrockAgentCore::Runtime',
    'AWS::BedrockAgentCore::RuntimeEndpoint'}
LIST_TAGS = {'AWS::CloudTrail::Trail', 'AWS::CloudWatch::Alarm', 'AWS::DynamoDB::Table',
    'AWS::IAM::Role', 'AWS::KMS::Key', 'AWS::Lambda::EventSourceMapping',
    'AWS::Lambda::Function', 'AWS::Logs::LogGroup', 'AWS::S3::Bucket',
    'AWS::SQS::Queue', 'AWS::SecretsManager::Secret'}

def annotate(template):
    description = template.get('Description', '')
    if WEBSITE not in description:
        template['Description'] = description + ' Implementation help: ' + WEBSITE
    template.setdefault('Metadata', {})['ProjectAttribution'] = ATTRIBUTION.copy()
    template.setdefault('Outputs', {})['ImplementationHelpUrl'] = {
        'Description': 'Contact Rohan Kataria for implementation help.', 'Value': WEBSITE}
    for resource in template['Resources'].values():
        props = resource.setdefault('Properties', {})
        if resource['Type'] in MAP_TAGS:
            props.setdefault('Tags', {}).update(ATTRIBUTION)
        elif resource['Type'] in LIST_TAGS:
            tags = {tag['Key']: tag['Value'] for tag in props.get('Tags', [])}
            tags.update(ATTRIBUTION)
            props['Tags'] = [{'Key': key, 'Value': value} for key, value in tags.items()]
    return template
