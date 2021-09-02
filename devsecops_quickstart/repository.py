import aws_cdk.core as cdk
import aws_cdk.aws_codecommit as codecommit


class Repository(cdk.Stack):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):
        super().__init__(scope, **kwargs)

        self.repository = codecommit.Repository(
            self, "Repository", repository_name=general_config["repository_name"]
        )

        cdk.CfnOutput(self, "Repository_Clone_URL", value=self.repository.repository_clone_url_http)
