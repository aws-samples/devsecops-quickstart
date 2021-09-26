import aws_cdk.core as cdk
import aws_cdk.aws_lambda_go as lambda_go
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_iam as iam
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deployment
import aws_cdk.aws_ssm as ssm
import aws_cdk.aws_kms as kms


class OPAScanStack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, general_config: dict, **kwargs):

        super().__init__(scope, id, **kwargs)

        lambda_role = iam.Role(
            self,
            "opa-scan-lambda-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, "lambda-service-basic-role", "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
        )

        lambda_policy = iam.Policy(self, "lambda-role-policy", statements=[iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["codepipeline:PutJobSuccessResult", "codepipeline:PutJobFailureResult"],
            resources=["*"],
        )])

        cfn_policy = lambda_policy.node.default_child
        cfn_policy.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {"id": "W12", "reason": ""},
                ]
            }
        }

        lambda_policy.attach_to_role(lambda_role)

        encryption_key = kms.Key(self, "opa-scan-rules-key")
        encryption_key.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:Decrypt", "kms:DescribeKey"],
                resources=["*"],
                principals=[iam.ArnPrincipal(lambda_role.role_arn)],
            )
        )

        rules_bucket = s3.Bucket(
            self,
            id="opa-scan-rules-bucket",
            bucket_name=f"opa-scan-rules-{self.account}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
        )

        cdk.Tags.of(rules_bucket).add("resource-owner", "opa-scan")

        s3_deployment.BucketDeployment(
            self,
            id="opa-scan-rules-deployment",
            destination_bucket=rules_bucket,
            sources=[s3_deployment.Source.asset("./devsecops_quickstart/opa_scan/rules")],
            memory_limit=128,
        )

        rules_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:List*", "s3:GetObject*", "s3:GetBucket*"],
                resources=[
                    rules_bucket.bucket_arn,
                    f"{rules_bucket.bucket_arn}/*",
                ],
                principals=[iam.ArnPrincipal(lambda_role.role_arn)],
            )
        )

        handler = lambda_go.GoFunction(
            self,
            "opa-scan",
            entry="devsecops_quickstart/opa_scan/lambda",
            role=lambda_role,
            environment={"RUN_ON_LAMBDA": "True"},
            timeout=cdk.Duration.minutes(2),
            memory_size=256,
            runtime=lambda_.Runtime.GO_1_X,
        )

        opa_scan_params = general_config["parameter_name"]["opa_scan"]
        ssm.StringParameter(
            self,
            "rules-bucket-url-ssm-param",
            parameter_name=opa_scan_params["rules_bucket"],
            string_value=rules_bucket.bucket_name,
        )

        ssm.StringParameter(
            self,
            "lambda-arn-ssm-param",
            parameter_name=opa_scan_params["lambda_arn"],
            string_value=handler.function_arn,
        )

        ssm.StringParameter(
            self,
            "role-arn-ssm-param",
            parameter_name=opa_scan_params["role_arn"],
            string_value=lambda_role.role_arn,
        )
