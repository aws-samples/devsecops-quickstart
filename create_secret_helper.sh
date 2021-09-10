SECRET_NAME=$1
SECRET_VALUE=$2
ACCOUNT=$(aws sts get-caller-identity --query Account)

SECRET_ARN=$(aws secretsmanager create-secret --name "$SECRET_NAME" --secret-string "$SECRET_VALUE" | jq '."ARN"')

SECRET_POLICY=$(cat << EOM
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": $ACCOUNT
      },
      "Action": [
        "secretsmanager:GetResourcePolicy",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:ListSecretVersionIds"
      ],
      "Resource": $SECRET_ARN
    }
  ]
}
EOM
)

aws secretsmanager put-resource-policy --secret-id "$SECRET_NAME" --resource-policy "$SECRET_POLICY"