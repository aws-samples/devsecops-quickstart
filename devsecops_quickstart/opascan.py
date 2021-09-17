import aws_cdk.core as cdk
import aws_cdk.aws_lambda_go as lambda_
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deployment


class OPAScanStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):

        super().__init__(scope, id="OPAScan", **kwargs)

        rules_bucket = s3.Bucket(
            self,
            id="opa-scan-rules-bucket",
            bucket_name=f"opa-scan-rules-{self.stack_name}-{self.account}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        s3_deployment.BucketDeployment(
            self,
            id="opa-scan-rules-deployment",
            destination_bucket=rules_bucket,
            sources=[s3_deployment.Source.asset("./devsecops_quickstart/opa-scan/rules")],
            memory_limit=128,
        )

        lambda_role = iam.Role(
            self,
            "opa-scan-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, "s3-full-access" "arn:aws:iam::aws:policy/AmazonS3FullAccess"
            )
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, "codepipeline-full-access" "arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess"
            )
        )

        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, "lambda-service-basic-role" "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
        )

        self.handler = lambda_.GoFunction(
            self,
            "opa-scan",
            entry="devsecops_quickstart/opa-scan/lambda",
            role=lambda_role,
            environment={"RUN_ON_LAMBDA": "True"},
        )
