# infra/infra/storage_stack.py
from aws_cdk import Stack, Duration, RemovalPolicy, aws_s3 as s3, aws_dynamodb as ddb
from constructs import Construct


class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.media = s3.Bucket(
            self, "Media",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            event_bridge_enabled=True,  # uploads become EventBridge events in week 2
            lifecycle_rules=[
                s3.LifecycleRule(prefix="raw/", expiration=Duration.days(14)),
                s3.LifecycleRule(prefix="previews/", expiration=Duration.days(7)),
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        self.table = ddb.TableV2(
            self, "State",
            partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing=ddb.Billing.on_demand(),
            removal_policy=RemovalPolicy.RETAIN,
        )