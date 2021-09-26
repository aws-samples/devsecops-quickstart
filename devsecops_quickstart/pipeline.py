import aws_cdk.aws_codebuild as codebuild
import aws_cdk.core as cdk
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.pipelines as pipelines
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_iam as iam

import aws_cdk.aws_lambda as lambda_
import aws_cdk.aws_ssm as ssm

import logging

from devsecops_quickstart.cloud9 import Cloud9Stack
from devsecops_quickstart.sample_app.sample_app import SampleAppStage

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ToolingStage(cdk.Stage):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):
        super().__init__(scope, id="tooling", **kwargs)

        Cloud9Stack(self, general_config=general_config, **kwargs)


class CICDPipelineStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        general_config: dict,
        stages_config: dict,
        is_development_pipeline: bool,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, stack_name=id, **kwargs)

        if is_development_pipeline:
            repository = codecommit.Repository(self, "Repository", repository_name=general_config["repository_name"])
        else:
            repository = codecommit.Repository.from_repository_name(
                self,
                id="Repository",
                repository_name=general_config["repository_name"],
            )

        # Defines the artifact representing the sourcecode
        source_artifact = codepipeline.Artifact()

        # Defines the artifact representing the cloud assembly (cloudformation template + all other assets)
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline = pipelines.CdkPipeline(
            self,
            f"{id}-pipeline",
            cloud_assembly_artifact=cloud_assembly_artifact,
            pipeline_name=id,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                repository=repository,
                branch=general_config["development_branch"]
                if is_development_pipeline
                else general_config["production_branch"],
                output=source_artifact,
                action_name="Source",
            ),
            synth_action=pipelines.SimpleSynthAction(
                cloud_assembly_artifact=cloud_assembly_artifact,
                source_artifact=source_artifact,
                install_commands=[
                    "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 "
                    "--storage-driver=overlay2 &",
                    'timeout 15 sh -c "until docker info; do echo .; sleep 1; done"',
                    "npm install aws-cdk -g",
                    "pip install -r requirements.txt",
                    "cd $HOME/.goenv && git pull --ff-only && cd -",
                    "goenv install 1.16.3",
                    "goenv local 1.16.3",
                    "go version",
                ],
                synth_command="npx cdk synth",
                test_commands=[
                    "python -m flake8 .",
                    "python -m black --check .",
                ],
                environment=codebuild.BuildEnvironment(privileged=True),
            ),
        )

        cdk.Tags.of(pipeline.code_pipeline.artifact_bucket).add("resource-owner", "pipeline")

        bandit_project = codebuild.PipelineProject(
            self,
            "Bandit",
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {"commands": ["pip install bandit"]},
                        "build": {"commands": ["python -m bandit -v -r devsecops_quickstart"]},
                    },
                }
            ),
        )
        snyk_project = codebuild.PipelineProject(
            self,
            "Snyk",
            role=iam.Role(
                self,
                "snyk-build-role",
                assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                inline_policies={
                    "GetSecretValue": iam.PolicyDocument(
                        statements=[
                            iam.PolicyStatement(
                                effect=iam.Effect.ALLOW,
                                actions=[
                                    "secretsmanager:GetSecretValue",
                                ],
                                resources=["*"],
                            )
                        ]
                    )
                },
            ),
            build_spec=codebuild.BuildSpec.from_object(
                {
                    "version": "0.2",
                    "phases": {
                        "install": {
                            "commands": [
                                "npm install -g snyk",
                                "pip install awscli --upgrade",
                                "pip install -r requirements.txt",
                            ]
                        },
                        "build": {
                            "commands": [
                                (
                                    "SNYK_TOKEN=$(aws secretsmanager get-secret-value "
                                    "--query SecretString --output text "
                                    f"--secret-id {general_config['secret_name']['snyk']} "
                                    f"--region {general_config['toolchain_region']})"
                                ),
                                "snyk test",
                                "snyk monitor",
                            ]
                        },
                    },
                }
            ),
        )

        opa_scan_params = general_config["parameter_name"]["opa_scan"]
        opa_scan_rules_bucket_name = ssm.StringParameter.value_from_lookup(
            self, parameter_name=opa_scan_params["rules_bucket"]
        )
        opa_scan_lambda_arn = ssm.StringParameter.value_from_lookup(self, parameter_name=opa_scan_params["lambda_arn"])
        opa_scan_role_arn = ssm.StringParameter.value_from_lookup(self, parameter_name=opa_scan_params["role_arn"])
        opa_scan_role = iam.Role.from_role_arn(self, "opa-scan-role", role_arn=opa_scan_role_arn)
        opa_scan_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["codepipeline:PutJobSuccessResult", "codepipeline:PutJobFailureResult"],
                resources=[pipeline.code_pipeline.pipeline_arn],
            )
        )

        cfn_nag_params = general_config["parameter_name"]["cfn_nag"]
        cfn_nag_lambda_arn = ssm.StringParameter.value_from_lookup(self, parameter_name=cfn_nag_params["lambda_arn"])
        cfn_nag_role_arn = ssm.StringParameter.value_from_lookup(self, parameter_name=cfn_nag_params["role_arn"])

        cfn_nag_role = iam.Role.from_role_arn(self, "cfn-nag-role", role_arn=cfn_nag_role_arn)
        cfn_nag_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["codepipeline:PutJobSuccessResult", "codepipeline:PutJobFailureResult"],
                resources=[pipeline.code_pipeline.pipeline_arn],
            )
        )

        pipeline.code_pipeline.artifact_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:List*", "s3:GetObject*", "s3:GetBucket*"],
                resources=[
                    pipeline.code_pipeline.artifact_bucket.bucket_arn,
                    f"{pipeline.code_pipeline.artifact_bucket.bucket_arn}/*",
                ],
                principals=[iam.ArnPrincipal(opa_scan_role_arn), iam.ArnPrincipal(cfn_nag_role_arn)],
            )
        )

        pipeline.code_pipeline.artifact_bucket.encryption_key.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["kms:Decrypt", "kms:DescribeKey"],
                resources=["*"],
                principals=[iam.ArnPrincipal(opa_scan_role_arn), iam.ArnPrincipal(cfn_nag_role_arn)],
            )
        )

        validate_stage = pipeline.add_stage("validate")
        validate_stage.add_actions(
            codepipeline_actions.CodeBuildAction(
                action_name="bandit",
                project=bandit_project,
                input=source_artifact,
                type=codepipeline_actions.CodeBuildActionType.TEST,
            ),
            codepipeline_actions.CodeBuildAction(
                action_name="snyk",
                project=snyk_project,
                input=source_artifact,
                type=codepipeline_actions.CodeBuildActionType.TEST,
            ),
            codepipeline_actions.LambdaInvokeAction(
                action_name="opa-scan",
                inputs=[cloud_assembly_artifact],
                lambda_=lambda_.Function.from_function_arn(self, "opa-scan-lambda", opa_scan_lambda_arn),
                user_parameters={"Rules": [f"s3://{opa_scan_rules_bucket_name}/cloudformation"]},
            ),
            codepipeline_actions.LambdaInvokeAction(
                action_name="cfn-nag",
                inputs=[cloud_assembly_artifact],
                lambda_=lambda_.Function.from_function_arn(self, "cfn-nag-lambda", cfn_nag_lambda_arn),
                # user_parameters must be a map, but cfn_nag requires a string
                # This property needs to be set manually in the console, until nag fixes this issue
                # user_parameters="**/*.template.json",
            ),
        )

        if is_development_pipeline:
            pipeline.add_application_stage(
                app_stage=ToolingStage(
                    self,
                    general_config=general_config,
                    env=cdk.Environment(
                        account=general_config["toolchain_account"],
                        region=general_config["toolchain_region"],
                    ),
                ),
            )

        for stage_config_item in stages_config.items():
            stage = stage_config_item[0]
            stage_config = stage_config_item[1]

            pipeline.add_application_stage(
                app_stage=SampleAppStage(
                    self,
                    stage=stage,
                    general_config=general_config,
                    stage_config=stage_config,
                    env=cdk.Environment(
                        account=stage_config["stage_account"],
                        region=stage_config["stage_region"],
                    ),
                )
            )

        cdk.CfnOutput(self, "pipeline-artifact-bucket", value=pipeline.code_pipeline.artifact_bucket.bucket_name)
