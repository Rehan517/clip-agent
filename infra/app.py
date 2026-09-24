# infra/app.py
import os

import aws_cdk as cdk

from infra.storage_stack import StorageStack

app = cdk.App()
env = cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"), region="us-east-1")
storage = StorageStack(app, "ClipStorage", env=env)
cdk.Tags.of(app).add("project", "clip-agent")
app.synth()