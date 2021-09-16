import aws_cdk.core as cdk
import aws_cdk.aws_lambda_go as lambda_


class OPAScanStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):

        super().__init__(scope, id="OPAScan", **kwargs)

        self.handler = lambda_.GoFunction(self, "opa-scan",
                  entry="devsecops_quickstart/opa-scan/lambda",
                  # bundling=lambda_.BundlingOptions(
                  #     forced_docker_bundling=True
                  # )
        )

