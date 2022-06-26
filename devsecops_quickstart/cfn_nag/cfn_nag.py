import aws_cdk.core as cdk
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_s3_deployment as s3_deployment
import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_iam as iam
import aws_cdk.aws_kms as kms


class CfnNag(cdk.Stack):
    def __init__(self, scope: cdk.Construct, id: str, general_config: dict, **kwargs):

        super().__init__(scope, id, **kwargs)

        lambda_role = iam.Role(
            self, "cfn-nag-role", role_name="cfn-nag-role", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )
        lambda_role.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self, "lambda-service-basic-role", "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
            )
        )

        lambda_policy = iam.Policy(
            self,
            "lambda-role-policy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["codepipeline:PutJobSuccessResult", "codepipeline:PutJobFailureResult"],
                    resources=["*"],
                )
            ],
        )

        cfn_policy = lambda_policy.node.default_child
        cfn_policy.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {"id": "W12", "reason": "Circular dependency, pipeline is not deployed yet"},
                ]
            }
        }

        lambda_policy.attach_to_role(lambda_role)

        encryption_key = kms.Key(self, "cfn-nag-rules-key", enable_key_rotation=True)
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
            id="cfn-nag-rules-bucket",
            bucket_name=f"cfn-nag-rules-{self.account}",
            removal_policy=cdk.RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=encryption_key,
        )

        cdk.Tags.of(rules_bucket).add("resource-owner", "cfn-nag")

        s3_deployment.BucketDeployment(
            self,
            id="cfn-nag-rules-deployment",
            destination_bucket=rules_bucket,
            sources=[s3_deployment.Source.asset("./devsecops_quickstart/cfn_nag/rules")],
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

        layer = lambda_.LayerVersion(
            self, 
            "cfn-nag-layer",
            code=lambda_.Code.from_asset("devsecops_quickstart/cfn_nag/layer.zip"),
            # code=lambda_.Code.from_asset("devsecops_quickstart/cfn_nag/cfn-nag-pipeline/layer"),
            compatible_runtimes=[lambda_.Runtime.RUBY_2_7],
            description="Ruby gems required for cfn-nag lambda handler"
        )

        # layer = lambda_.LayerVersion(
        #     self, 
        #     "cfn-nag-layer",
        #     code=lambda_.Code.from_asset(
        #         path="devsecops_quickstart/cfn_nag/cfn-nag-pipeline",
        #         bundling=cdk.BundlingOptions(
        #             image=cdk.DockerImage("amazon/aws-sam-cli-build-image-ruby2.7"),
        #             command=[
        #                 'echo "!!!!!! HELLO WORLD"',
        #                 # "bundle install --path=ruby/gems"
        #                 # "mv ruby/gems/ruby/* ruby/gems/",
        #                 # "rm -rf ruby/gems/2.7.0/cache",
        #                 # "rm -rf ruby/gems/ruby",
        #                 # "mkdir layer",
        #                 # "mv ruby layer",
        #                 # "cp layer /asset-output"
        #             ]
        #         )
        #     ),
        #     compatible_runtimes=[lambda_.Runtime.RUBY_2_7],
        #     description="Ruby gems required for cfn-nag lambda handler"
        # )

        lambda_.Function(
            self,
            "cfn-nag-handler",
            function_name="cfn-nag",
            runtime=lambda_.Runtime.RUBY_2_7,
            memory_size=1024,
            timeout=cdk.Duration.seconds(300),
            handler="handler.handler",
            layers=[layer],
            role=lambda_role,
            code=lambda_.Code.from_asset("devsecops_quickstart/cfn_nag/cfn-nag-pipeline/lib"),
            environment={"RULE_BUCKET_NAME": rules_bucket.bucket_name, "RuleBucketPrefix": ""},
        )
