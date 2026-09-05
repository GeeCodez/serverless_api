#!/usr/bin/env python3
import os

import aws_cdk as cdk

from serverless_api.serverless_api_stack import ServerlessApiStack


app = cdk.App()
ServerlessApiStack(app, "ServerlessApiStack",env=cdk.Environment(account=os.getenv('CDK_DEFAULT_ACCOUNT'), region=os.getenv('CDK_DEFAULT_REGION')))

app.synth()
