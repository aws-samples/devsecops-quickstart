from aws_cdk import core as cdk

# import aws_cdk.aws_ssm as ssm
# import aws_cdk.aws_s3 as s3


class SampleApp(cdk.Stack):
    def __init__(self, scope: cdk.Construct, stage: str, general_config: dict, stage_config: dict, **kwargs):

        super().__init__(scope, id="SampleApp", **kwargs)

        # The code that defines your stack goes here

        # opa_scan_lambda_arn = ssm.StringParameter.from_string_parameter_name(
        #     self, "lambda-arn-ssm-param", "doesntexist"
        # )
        #
        # rules_bucket = s3.Bucket(
        #     self,
        #     id="sample-bucket",
        #     bucket_name=f"sample-bucket-{self.account}",
        #     removal_policy=cdk.RemovalPolicy.DESTROY,
        #     block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        # )


class SampleAppStage(cdk.Stage):
    def __init__(self, scope: cdk.Construct, stage: str, general_config: dict, stage_config: dict, **kwargs):
        super().__init__(scope, id=stage, **kwargs)

        SampleApp(self, stage, general_config, stage_config, **kwargs)
