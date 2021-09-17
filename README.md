
# Welcome to your CDK Python project!

This is a blank project for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

Update `cdk.json` witn account and region values for deployment of toolchain and Dev stacks. Optionally, 
uncomment and update QA and Prod stages if you want to do multi-account deployments.

Bootstrap the toolchain account. You only need to do this one time per environment where you want 
to deploy CDK applications.

Make sure you have credentials for the toolchain account in a profile named `toolchain-profile`.

```
$ cdk bootstrap \
  --profile toolchain-profile \
  --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
  aws://<toolchain-account>/<toolchain-region>
```

Bootstrap the target accounts. You only need to do this one time per environment where you want
to deploy CDK applications.

Make sure you have credentials for the development account in a profile named `dev-profile`.

```
$ cdk bootstrap \
  --profile dev-profile \
  --trust <toolchain-account> \
  --cloudformation-execution-policies arn:aws:iam::aws:policy/AdministratorAccess \
  aws://<dev-account>/<dev-region>
```

Repeat this step for your qa and prod accounts.

At this point you can now synthesize the CloudFormation template for this code.

Run the following command to list all CDK apps defined.

```
$ cdk ls
```

Create new secret containing Snyk authentication token for snyk integration:
```
$ ./create_secret_helper.sh snyk-auth-token <snyk-auth-token-value>
```


Deploy the AWS CodeCommit repository in the toolchain account. The repository name will be taken from 
the `repository_name` config parameter in `cdk.json`.

```
$ cdk deploy devsecops-quickstart-repository --profile toolchain-profile
```

Take note of the `devsecops-quickstart-repository.RepositoryCloneURL` value in the deployment Outputs.

Initiate git and commit to new repository.
```
$ git init
$ git remote add origin https://git-codecommit.eu-west-1.amazonaws.com/v1/repos/devsecops-quickstart
$ git checkout -b development
$ git add .
$ git commit -m "initial commit"
$ git push --set-upstream origin development
```

Run the following command to deploy OPA Scan stack into toolchain account.

```
$ cdk deploy devsecops-quickstart-opa-scan --profile toolchain-profile
```

Run the following command to deploy the development CI/CD pipeline. The development pipeline will track changes from
`development_branch` as configured in `cdk.json`. 

```
$ cdk deploy devsecops-quickstart-cicd-development --profile toolchain-profile
```

Run the following command to deploy the production CI/CD pipeline. The production pipeline will track changes from
`production_branch` as configured in `cdk.json`.

```
$ cdk deploy devsecops-quickstart-production --profile toolchain-profile
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
