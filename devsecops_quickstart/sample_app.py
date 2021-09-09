from aws_cdk import core as cdk


class SampleApp(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        stage: str,
        general_config: dict,
        stage_config: dict,
        **kwargs
    ):

        super().__init__(scope, id="SampleApp", **kwargs)

        # The code that defines your stack goes here


class SampleAppStage(cdk.Stage):
    def __init__(
        self,
        scope: cdk.Construct,
        stage: str,
        general_config: dict,
        stage_config: dict,
        **kwargs
    ):
        super().__init__(scope, id=stage, **kwargs)

        SampleApp(self, stage, general_config, stage_config, **kwargs)
