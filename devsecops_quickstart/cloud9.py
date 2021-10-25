import aws_cdk.aws_cloud9 as cloud9
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_iam as iam
import aws_cdk.aws_secretsmanager as secretmanager
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

        secret = secretmanager.Secret(  # nosec
            self,
            id="cloud9_admin_password",
            secret_name="cloud9_admin_password",
            description="cloud9 admin password",
        )

        cloud9_admin_user = iam.User(
            self,
            id="cloud9_admin",
            user_name="cloud9_admin",
            password=secret.secret_value,
        )
        cloud9_admin_user.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                id="AWSCloud9Administrator",
                managed_policy_arn="arn:aws:iam::aws:policy/AWSCloud9Administrator",
            )
        )
        cloud9_admin_user.add_managed_policy(
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                id="AWSCodeCommitFullAccess",
                managed_policy_arn="arn:aws:iam::aws:policy/AWSCodeCommitFullAccess",
            )
        )

        vpc = ec2.Vpc(self, "Cloud9-VPC", max_azs=3)

        cloud9_environment = cloud9.CfnEnvironmentEC2(
            self,
            general_config["repository_name"],
            instance_type="t2.micro",
            automatic_stop_time_minutes=30,
            owner_arn=cloud9_admin_user.user_arn,
            subnet_id=vpc.public_subnets[0].subnet_id,
            repositories=[
                cloud9.CfnEnvironmentEC2.RepositoryProperty(
                    repository_url=repository.repository_clone_url_http,
                    path_component=f"/{general_config['repository_name']}",
                )
            ],
        )

        ide_url = "https://{region}.console.aws.amazon.com/cloud9/ide/{id}".format(
            region=general_config["toolchain_region"], id=cloud9_environment.ref
        )

        secret_url = (
            "https://{region}.console.aws.amazon.com/secretsmanager/home?region={region}#!/secret?name={secret}".format(
                region=general_config["toolchain_region"], secret=secret.secret_name
            )
        )

        cdk.CfnOutput(self, "IDE_Account", value=general_config["toolchain_account"])
        cdk.CfnOutput(self, "IDE_URL", value=ide_url)
        cdk.CfnOutput(self, "Admin_User_Name", value=cloud9_admin_user.user_name)
        cdk.CfnOutput(self, "Admin_Password_Secret_URL", value=secret_url)

        cloud9_admin_user.node.default_child.cfn_options.metadata = {
            "cfn_nag": {
                "rules_to_suppress": [
                    {"id": "F2000", "reason": "Single user for Cloud9 admin"},
                ]
            }
        }
