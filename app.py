#!/usr/bin/env python3
from aws_cdk import core as cdk
from devsecops_quickstart.pipeline import CICDPipelineStack

app = cdk.App()
config = app.node.try_get_context("config")
general_config = config["general"]

developmentPipeline = CICDPipelineStack(
    app,
    id=f"{general_config['repository_name']}-cicd",
    general_config=general_config,
    stages_config=config["stage"],
    env=cdk.Environment(
        account=general_config["toolchain_account"],
        region=general_config["toolchain_region"],
    ),
)

app.synth()
