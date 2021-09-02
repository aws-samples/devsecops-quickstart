import aws_cdk.aws_cloud9 as cloud9
import aws_cdk.aws_ec2 as ec2
import aws_cdk.core as cdk
import aws_cdk.aws_codecommit as codecommit


class Cloud9Stack(cdk.Stack):
    def __init__(self, scope: cdk.Construct, general_config: dict, **kwargs):
        super().__init__(scope, id="Cloud9", **kwargs)

        repository = codecommit.Repository.from_repository_name(
            self,
            id="Repository",
            repository_name=general_config["repository_name"],
        )

        vpc = ec2.Vpc(self, "Cloud9-VPC", max_azs=3)
        c9env = cloud9.Ec2Environment(
            self,
            "Cloud9-Env",
            vpc=vpc,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            cloned_repositories=[
                cloud9.CloneRepository.from_code_commit(repository, "/"),
            ],
        )

        cdk.CfnOutput(self, "Cloud9_IDE_URL", value=c9env.ide_url)


class Cloud9Stage(cdk.Stage):
    def __init__(
        self, scope: cdk.Construct, stage: str, general_config: dict, **kwargs
    ):
        super().__init__(scope, id=stage, **kwargs)

        Cloud9Stack(self, general_config=general_config, **kwargs)
