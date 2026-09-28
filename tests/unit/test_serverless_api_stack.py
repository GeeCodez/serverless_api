import aws_cdk as core
import aws_cdk.assertions as assertions

from serverless_api.serverless_api_stack import ServerlessApiStack

def test_product_image_bucket_is_private_versioned_and_retained():
    app = core.App()
    stack = ServerlessApiStack(app, "serverless-api")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::S3::Bucket", {
        "VersioningConfiguration": {"Status": "Enabled"},
        "PublicAccessBlockConfiguration": {
            "BlockPublicAcls": True,
            "BlockPublicPolicy": True,
            "IgnorePublicAcls": True,
            "RestrictPublicBuckets": True,
        },
        "LifecycleConfiguration": assertions.Match.object_like({
            "Rules": assertions.Match.array_with([
                assertions.Match.object_like({
                    "ID": "ProductImageLifecycle",
                    "Status": "Enabled",
                    "ExpirationInDays": 2555,
                })
            ])
        }),
    })


def test_image_processor_has_retry_destination():
    app = core.App()
    stack = ServerlessApiStack(app, "serverless-api")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties("AWS::Lambda::EventInvokeConfig", {
        "MaximumRetryAttempts": 2,
        "MaximumEventAgeInSeconds": 3600,
    })
