from aws_cdk import (
    Stack,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    CfnOutput
)
from constructs import Construct

class ServerlessApiStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        lambda_kwargs = {
            "runtime": _lambda.Runtime.PYTHON_3_12,
            "code": _lambda.Code.from_asset("lambda"),
        }

        get_product_fn = _lambda.Function(
            self, "GetProductHandler", handler="get_product.handler", **lambda_kwargs
        )
        query_products_fn = _lambda.Function(
            self, "QueryProductsHandler", handler="query_products.handler", **lambda_kwargs
        )
        insert_product_fn = _lambda.Function(
            self, "InsertProductHandler", handler="insert_product.handler", **lambda_kwargs
        )
        update_product_fn = _lambda.Function(
            self, "UpdateProductHandler", handler="update_product.handler", **lambda_kwargs
        )
        options_fn = _lambda.Function(
            self, "OptionsHandler", handler="options.handler", **lambda_kwargs
        )

        api = apigw.RestApi(
            self, "ProductCatalogAPI",
            rest_api_name="Product Catalog Service",
            description="Serverless Product Catalog API"
        )

        products = api.root.add_resource("products")
        products.add_method("GET", apigw.LambdaIntegration(query_products_fn))
        products.add_method("POST", apigw.LambdaIntegration(insert_product_fn))
        products.add_method("OPTIONS", apigw.LambdaIntegration(options_fn))

        product_by_id = products.add_resource("{id}")
        product_by_id.add_method("GET", apigw.LambdaIntegration(get_product_fn))
        product_by_id.add_method("PUT", apigw.LambdaIntegration(update_product_fn))
        product_by_id.add_method("OPTIONS", apigw.LambdaIntegration(options_fn))

        CfnOutput(self, "ProductsApiUrl", value=api.url)