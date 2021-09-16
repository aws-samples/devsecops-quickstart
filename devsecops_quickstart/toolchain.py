import aws_cdk.core as cdk

from devsecops_quickstart.cloud9 import Cloud9Stack
from devsecops_quickstart.opascan import OPAScanStack


class ToolchainStage(cdk.Stage):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):
        super().__init__(scope, id="toolchain", **kwargs)

        Cloud9Stack(self, general_config=general_config, **kwargs)
        OPAScanStack(self, general_config=general_config, **kwargs)