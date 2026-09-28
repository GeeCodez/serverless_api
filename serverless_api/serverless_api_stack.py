from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cognito as cognito,
    aws_cloudwatch as cloudwatch,
    aws_dynamodb as dynamodb,
    aws_iam as iam,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_lambda_destinations as lambda_destinations,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_notifications as s3_notifications,
    aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_elasticache_alpha as elasticache,
)
from constructs import Construct


class ServerlessApiStack(Stack):
    """Declare the product API, image storage, access control, and processing resources."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """Create durable storage and connect the API and asynchronous image workflow."""
        super().__init__(scope, construct_id, **kwargs)

        allowed_origins = self.node.try_get_context("imageUploadAllowedOrigins")
        if allowed_origins is None:
            allowed_origins = ["http://localhost:3000"]
        elif isinstance(allowed_origins, str):
            allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]
        if not allowed_origins or "*" in allowed_origins:
            raise ValueError("Set imageUploadAllowedOrigins to one or more explicit origins; '*' is not allowed.")

        image_key = kms.Key(
            self,
            "ProductImagesKey",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
            description="Encrypt product image objects stored in S3.",
        )
        product_images_bucket = s3.Bucket(
            self,
            "ProductImagesBucket",
            bucket_name=f"product-catalog-images-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=image_key,
            bucket_key_enabled=True,
            versioned=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.POST],
                    allowed_origins=allowed_origins,
                    allowed_headers=["content-type"],
                    exposed_headers=["ETag"],
                    max_age=300,
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="ProductImageLifecycle",
                    enabled=True,
                    prefix="products/",
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        ),
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        ),
                    ],
                    expiration=Duration.days(2555),
                    noncurrent_version_transitions=[
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(90),
                        )
                    ],
                    noncurrent_version_expiration=Duration.days(2555),
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        products_table = dynamodb.Table(
            self,
            "ProductsTable",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True,
            ),
            removal_policy=RemovalPolicy.RETAIN,
        )
        products_table.add_global_secondary_index(
            index_name="category-index",
            partition_key=dynamodb.Attribute(name="category", type=dynamodb.AttributeType.STRING),
        )

        dependencies_layer = _lambda.LayerVersion(
            self,
            "DependenciesLayer",
            code=_lambda.Code.from_asset(
                "lambda_layer",
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache-dir -r requirements.txt -t /asset-output/python",
                    ],
                ),
            ),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description="Python dependencies shared by API and image-processing functions.",
        )
        
        vpc = ec2.Vpc(
            self,
            "ProductApiVpc",
            max_azs=3,
            nat_gateways=0,
        )
        
        vpc.add_gateway_endpoint(
            "DynamoDbEndpoint",
            service=ec2.GatewayVpcEndpointAwsService.DYNAMODB,
        )

        lambda_sg = ec2.SecurityGroup(
            self,
            "ProductLambdaSecurityGroup",
            vpc=vpc,
            description="Security group for product API Lambdas",
            allow_all_outbound=True,
        )

        cache_sg = ec2.SecurityGroup(
            self,
            "ProductCacheSecurityGroup",
            vpc=vpc,
            description="Security group for Valkey cache",
            allow_all_outbound=True,
        )
        
        cache = elasticache.ServerlessCache(
            self,
            "ProductCache",
            engine=elasticache.CacheEngine.VALKEY_LATEST,
            vpc=vpc,
            security_groups=[cache_sg],
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            ),
        )

        cache_sg.add_ingress_rule(
            lambda_sg,
            ec2.Port.tcp_range(6379, 6380),
            "Allow product Lambdas to access Valkey",
        )

        common_environment = {
            "TABLE_NAME": products_table.table_name,
            "IMAGES_BUCKET_NAME": product_images_bucket.bucket_name,
            "ALLOWED_ORIGIN": allowed_origins[0],
            "CACHE_ENDPOINT": cache.serverless_cache_endpoint_address,
            "CACHE_PORT": str(cache.serverless_cache_endpoint_port),
        }
        
        def create_function(identifier, handler, *, environment=None, **overrides):
            """Create consistently packaged Python functions with bounded logs and timeouts."""
            merged_environment = {**common_environment, **(environment or {})}
            return _lambda.Function(
                self,
                identifier,
                runtime=_lambda.Runtime.PYTHON_3_12,
                code=_lambda.Code.from_asset("lambda_func"),
                handler=handler,
                layers=[dependencies_layer],
                environment=merged_environment,
                timeout=Duration.seconds(30),
                memory_size=512,
                log_retention=logs.RetentionDays.ONE_MONTH,
                **overrides,
            )

        get_product_fn = create_function("GetProductHandler", "get_product.handler", vpc=vpc, security_groups=[lambda_sg])
        query_products_fn = create_function("QueryProductsHandler", "query_products.handler", vpc=vpc, security_groups=[lambda_sg])
        insert_product_fn = create_function("InsertProductHandler", "insert_product.handler")
        update_product_fn = create_function("UpdateProductHandler", "update_product.handler", vpc=vpc, security_groups=[lambda_sg])
        options_fn = create_function("OptionsHandler", "options.handler")
        upload_image_fn = create_function("UploadImageHandler", "upload_image.handler")
        download_image_fn = create_function("DownloadImageHandler", "download_image.handler")

        image_processing_dlq = sqs.Queue(
            self,
            "ImageProcessingDeadLetterQueue",
            encryption=sqs.QueueEncryption.SQS_MANAGED,
            retention_period=Duration.days(14),
            enforce_ssl=True,
        )
        process_image_fn = create_function(
            "ProcessProductImageHandler",
            "process_product_image.handler",
        )

        # Keep DynamoDB permissions at the function boundary and limited to table APIs used.
        products_table.grant_read_data(get_product_fn)
        products_table.grant_read_data(query_products_fn)
        products_table.grant_write_data(insert_product_fn)
        products_table.grant_read_write_data(update_product_fn)
        for function in (upload_image_fn, download_image_fn, process_image_fn):
            function.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["dynamodb:GetItem", "dynamodb:UpdateItem"],
                    resources=[products_table.table_arn],
                )
            )

        # Restrict client-generated writes to pending originals and processor writes to derivatives.
        product_images_bucket.grant_put(upload_image_fn, "products/uploads/*")
        product_images_bucket.grant_read(download_image_fn, "products/processed/*")
        download_image_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:RestoreObject"],
                resources=[product_images_bucket.arn_for_objects("products/processed/*")],
            )
        )
        product_images_bucket.grant_read(process_image_fn, "products/uploads/*")
        product_images_bucket.grant_put(process_image_fn, "products/processed/*")
        for function in (upload_image_fn, download_image_fn, process_image_fn):
            image_key.grant_encrypt_decrypt(function)

        # Cognito is the API identity provider; write routes require a verified user token.
        user_pool = cognito.UserPool(
            self,
            "ProductCatalogUserPool",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            mfa=cognito.Mfa.OPTIONAL,
            removal_policy=RemovalPolicy.RETAIN,
        )
        user_pool_client = user_pool.add_client(
            "ProductCatalogApiClient",
            auth_flows=cognito.AuthFlow(user_password=True, user_srp=True),
            prevent_user_existence_errors=True,
        )
        authorizer = apigw.CognitoUserPoolsAuthorizer(
            self,
            "ProductCatalogAuthorizer",
            cognito_user_pools=[user_pool],
        )

        api = apigw.RestApi(
            self,
            "ProductCatalogAPI",
            rest_api_name="Product Catalog Service",
            description="Product catalog with private S3 image storage.",
            default_method_options=apigw.MethodOptions(),
        )
        authenticated = apigw.MethodOptions(
            authorization_type=apigw.AuthorizationType.COGNITO,
            authorizer=authorizer,
        )

        products = api.root.add_resource("products")
        products.add_method("GET", apigw.LambdaIntegration(query_products_fn))
        products.add_method("POST", apigw.LambdaIntegration(insert_product_fn), authorizer=authorizer)
        products.add_method("OPTIONS", apigw.LambdaIntegration(options_fn))

        product_by_id = products.add_resource("{id}")
        product_by_id.add_method("GET", apigw.LambdaIntegration(get_product_fn))
        product_by_id.add_method("PUT", apigw.LambdaIntegration(update_product_fn), authorizer=authorizer)
        product_by_id.add_method("OPTIONS", apigw.LambdaIntegration(options_fn))

        images = product_by_id.add_resource("images")
        upload_url = images.add_resource("upload-url")
        upload_url.add_method("POST", apigw.LambdaIntegration(upload_image_fn), authorizer=authorizer)
        upload_url.add_method("OPTIONS", apigw.LambdaIntegration(options_fn))

        image_by_id = images.add_resource("{image_id}")
        download_url = image_by_id.add_resource("download-url")
        download_url.add_method("GET", apigw.LambdaIntegration(download_image_fn))
        download_url.add_method("OPTIONS", apigw.LambdaIntegration(options_fn))

        # S3 only watches the raw-upload prefix; generated derivatives cannot retrigger this function.
        product_images_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3_notifications.LambdaDestination(process_image_fn),
            s3.NotificationKeyFilter(prefix="products/uploads/"),
        )
        _lambda.EventInvokeConfig(
            self,
            "ProcessImageAsyncConfig",
            function=process_image_fn,
            max_event_age=Duration.hours(1),
            retry_attempts=2,
            on_failure=lambda_destinations.SqsDestination(image_processing_dlq),
        )
        cloudwatch.Alarm(
            self,
            "ImageProcessingDlqAlarm",
            metric=image_processing_dlq.metric_approximate_number_of_messages_visible(),
            threshold=1,
            evaluation_periods=1,
            datapoints_to_alarm=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )

        CfnOutput(self, "ProductsApiUrl", value=api.url)
        CfnOutput(self, "ImagesBucketName", value=product_images_bucket.bucket_name)
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(self, "ImageProcessingDlqUrl", value=image_processing_dlq.queue_url)