import aws_cdk.aws_codebuild as codebuild
import aws_cdk.core as cdk
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.pipelines as pipelines
import aws_cdk.aws_codecommit as codecommit
import aws_cdk.aws_iam as iam

import aws_cdk.aws_lambda as lambda_

import logging

from devsecops_quickstart.cloud9 import Cloud9Stack
from devsecops_quickstart.opa_scan.opascan import OPAScanStack
from devsecops_quickstart.cfn_nag.cfn_nag import CfnNagStack
from devsecops_quickstart.sample_app.sample_app import SampleAppStage

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ToolingStage(cdk.Stage):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):
        super().__init__(scope, id="tooling", **kwargs)

        Cloud9Stack(self, general_config=general_config, **kwargs)

        OPAScanStack(self, general_config=general_config)

        CfnNagStack(self, general_config=general_config)


class CICDPipelineStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        id: str,
        general_config: dict,
        stages_config: dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, stack_name=id, **kwargs)

        cfn_nag_role = iam.Role(
            self, "cfn-nag-role", role_name="cfn-nag-role", assumed_by=iam.ServicePrincipal("lambda.amazonaws.com")
        )

        opa_scan_role = iam.Role(
            self,
            "opa-scan-role",
            role_name="opa-scan-role",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )

        # repository = codecommit.Repository(self, "Repository", repository_name=general_config["repository_name"])

        repository = codecommit.Repository.from_repository_name(
            self,
            id="Repository",
            repository_name=general_config["repository_name"],
        )

        cdk.CfnOutput(self, "repository-url", value=repository.repository_clone_url_http)

        # Defines the artifact representing the sourcecode
        source_artifact = codepipeline.Artifact()

        # Defines the artifact representing the cloud assembly (cloudformation template + all other assets)
        cloud_assembly_artifact = codepipeline.Artifact()

        source_action = codepipeline_actions.CodeCommitSourceAction(
            repository=repository,
            branch=general_config["repository_branch"],
            output=source_artifact,
            action_name="Source",
        )

        synth_action = pipelines.SimpleSynthAction(
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_artifact=source_artifact,
            install_commands=[
                "nohup /usr/local/bin/dockerd --host=unix:///var/run/docker.sock --host=tcp://127.0.0.1:2375 "
                "--storage-driver=overlay2 &",
                'timeout 15 sh -c "until docker info; do echo .; sleep 1; done"',
            ]
            + [
                "npm install aws-cdk -g",
                "pip install -r requirements.txt",
            ]
            + [
                "cd $HOME/.goenv && git pull --ff-only && cd -",
                "goenv install 1.16.3",
                "goenv local 1.16.3",
                "go version",
            ]
            + [
                "git init",
                "cd devsecops_quickstart/cfn_nag",
                "git submodule add https://github.com/stelligent/cfn-nag-pipeline.git",
                "ls cfn-nag-pipeline",
                "cd -",
            ],
            synth_command="npx cdk synth",
            test_commands=[
                "python -m flake8 .",
                "python -m black --check .",
            ],
            environment=codebuild.BuildEnvironment(privileged=True),
            role_policy_statements=[
                iam.PolicyStatement(effect=iam.Effect.ALLOW, actions=["sts:assumeRole"], resources=["*"])
            ],
        )

        pipeline = pipelines.CdkPipeline(
            self,
            f"{id}-pipeline",
            cloud_assembly_artifact=cloud_assembly_artifact,
            pipeline_name=id,
            source_action=source_action,
            synth_action=synth_action,
        )

        pipeline_artifact_bucket = pipeline.code_pipeline.artifact_bucket
        pipeline_artifact_bucket.grant_read(cfn_nag_role)
        pipeline_artifact_bucket.grant_read(opa_scan_role)
        cdk.CfnOutput(self, "pipeline-artifact-bucket", value=pipeline_artifact_bucket.bucket_name)

        cdk.Tags.of(pipeline_artifact_bucket).add("resource-owner", "pipeline")

        # FIXME
        pipeline_artifact_bucket.encryption_key.node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {"id": "F19", "reason": "CDK Generated Resource for Pipeline Artifacts"},
                ]
            }
        }

        # git_submodules is currently not supported for CODEPIPELINE type
        # synth_action.project.node.default_child.source = codebuild.CfnProject.SourceProperty(
        #     type="CODEPIPELINE",
        #     git_submodules_config=codebuild.CfnProject.GitSubmodulesConfigProperty(fetch_submodules=True),
        # )

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
                                "n lts",
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

        pipeline.add_application_stage(
            app_stage=ToolingStage(
                self,
                general_config=general_config
            ),
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
                lambda_=lambda_.Function.from_function_arn(
                    self, "opa-scan-lambda", f"arn:aws:lambda:{self.region}:{self.account}:function:opa-scan"
                ),
                user_parameters={"Rules": [f"s3://opa-scan-rules-{self.account}/cloudformation"]},
            ),
            codepipeline_actions.LambdaInvokeAction(
                action_name="cfn-nag",
                inputs=[cloud_assembly_artifact],
                lambda_=lambda_.Function.from_function_arn(
                    self, "cfn-nag-lambda", f"arn:aws:lambda:{self.region}:{self.account}:function:cfn-nag"
                ),
                user_parameters_string="**/*.template.json",
            ),
        )

        for stage_config_item in stages_config.items():
            stage = stage_config_item[0]
            stage_config = stage_config_item[1]

            pipeline.add_application_stage(
                manual_approvals=stage_config["manual_approvals"],
                app_stage=SampleAppStage(
                    self,
                    stage=stage,
                    general_config=general_config,
                    stage_config=stage_config,
                    env=cdk.Environment(
                        account=stage_config["stage_account"],
                        region=stage_config["stage_region"],
                    ),
                ),
            )
