import aws_cdk.aws_codebuild as codebuild
import aws_cdk.core as cdk
import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions
import aws_cdk.pipelines as pipelines
import aws_cdk.aws_codecommit as codecommit

import logging

from devsecops_quickstart.cloud9 import Cloud9Stage
from devsecops_quickstart.sample_app.sample_app import SampleAppStage

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class CICDPipeline(cdk.Stack):
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
            repository = codecommit.Repository(
                self, "Repository", repository_name=general_config["repository_name"]
            )
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
                    "npm install -g snyk",
                    "pip install -r requirements.txt",
                ],
                synth_command="npx cdk synth",
                test_commands=[
                    "python -m flake8 .",
                    "python -m black --check .",
                    "python -m bandit -v -r devsecops_quickstart",
                ],
                environment=codebuild.BuildEnvironment(privileged=True),
            ),
        )

        if is_development_pipeline:
            pipeline.add_application_stage(
                app_stage=Cloud9Stage(
                    self,
                    stage="toolchain",
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
