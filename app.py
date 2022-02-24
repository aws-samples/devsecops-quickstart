#!/usr/bin/env python3
from aws_cdk import core as cdk

from devsecops_quickstart.opa_scan.opascan import OPAScanStack
from devsecops_quickstart.cfn_nag.cfn_nag import CfnNag
from devsecops_quickstart.pipeline import CICDPipelineStack

app = cdk.App()
config = app.node.try_get_context("config")
general_config = config["general"]

opa_scan = OPAScanStack(
    app,
    id=f"{general_config['repository_name']}-opa-scan",
    general_config=general_config,
    env=cdk.Environment(
        account=general_config["toolchain_account"],
        region=general_config["toolchain_region"],
    ),
)

cfn_nag = CfnNag(
    app,
    id=f"{general_config['repository_name']}-cfn-nag",
    general_config=general_config,
    env=cdk.Environment(
        account=general_config["toolchain_account"],
        region=general_config["toolchain_region"],
    ),
)

developmentPipeline = CICDPipelineStack(
    app,
    id=f"{general_config['repository_name']}-cicd-development",
    general_config=general_config,
    stages_config=dict(filter(lambda item: item[0] == "dev", config["stage"].items())),
    is_development_pipeline=True,
    env=cdk.Environment(
        account=general_config["toolchain_account"],
        region=general_config["toolchain_region"],
    ),
)

productionPipeline = CICDPipelineStack(
    app,
    id=f"{general_config['repository_name']}-cicd-production",
    general_config=general_config,
    stages_config=dict(filter(lambda item: item[0] in ["qa", "prod"], config["stage"].items())),
    is_development_pipeline=False,
    env=cdk.Environment(
        account=general_config["toolchain_account"],
        region=general_config["toolchain_region"],
    ),
)

app.synth()
