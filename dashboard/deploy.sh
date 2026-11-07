#!/usr/bin/env bash
# Deploy Channel Studio to YOUR AWS account (CloudFormation stack: S3 + CloudFront, one Lambda, DynamoDB on demand,
# a Cognito user pool where only invited emails can sign in). Costs about $0 a month at personal scale.
#
#   STACK=chstudio AUTH_PREFIX=mychannels-studio ALLOWED=you@example.com ./dashboard/deploy.sh
#   Optional custom domain: CERT_ARN=<ACM cert in us-east-1> ALIAS=studio.example.com (then point a CNAME/alias at the
#   CloudFront domain the script prints).
set -euo pipefail
cd "$(dirname "$0")"
: "${STACK:=chstudio}" "${AUTH_PREFIX:?set AUTH_PREFIX, a globally unique Cognito domain prefix}" "${ALLOWED:?set ALLOWED, the emails allowed to sign in}"
: "${SSM_PREFIX:=/chstudio}" "${AWS_REGION:=us-east-1}"
export AWS_REGION
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
CODE_BUCKET=${CODE_BUCKET:-$STACK-code-$ACCOUNT}
aws s3api head-bucket --bucket "$CODE_BUCKET" 2>/dev/null || aws s3 mb "s3://$CODE_BUCKET" >/dev/null
B=$(mktemp -d)
python3 -m pip install -q --disable-pip-version-check --target "$B" --platform manylinux2014_aarch64 --implementation cp \
  --python-version 3.12 --only-binary=:all: "PyJWT[crypto]==2.10.1" >/dev/null
cp api/app.py "$B/"
KEY=api-$(date +%Y%m%d%H%M%S).zip
(cd "$B" && zip -qr "/tmp/$KEY" .)
aws s3 cp --only-show-errors "/tmp/$KEY" "s3://$CODE_BUCKET/$KEY" && rm -rf "$B" "/tmp/$KEY"
PARAMS=(CodeBucket="$CODE_BUCKET" CodeKey="$KEY" AllowedEmails="$ALLOWED" AuthDomainPrefix="$AUTH_PREFIX" SsmPrefix="$SSM_PREFIX" TableName="$STACK")
[ -n "${ALIAS:-}" ] && [ -n "${CERT_ARN:-}" ] && PARAMS+=(CertArn="$CERT_ARN" Alias="$ALIAS")
aws cloudformation deploy --stack-name "$STACK" --template-file infra/template.yaml --capabilities CAPABILITY_IAM \
  --parameter-overrides "${PARAMS[@]}" --no-fail-on-empty-changeset
out() { aws cloudformation describe-stacks --stack-name "$STACK" --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" --output text; }
aws ssm put-parameter --name "$SSM_PREFIX/client_id" --type String --overwrite --value "$(out ClientId)" >/dev/null
printf 'window.STUDIO = {clientId: "%s", domain: "%s"};\n' "$(out ClientId)" "$(out CognitoDomain)" > web/config.js
aws s3 sync web "s3://$(out WebBucket)" --delete --cache-control "no-cache" >/dev/null
aws cloudfront create-invalidation --distribution-id "$(out DistId)" --paths "/*" >/dev/null
echo "Channel Studio: https://$(out DistDomain)/   (user pool $(out UserPoolId))"
echo "Next: dashboard/add_channel.py for each channel, dashboard/setup_keys.py once, then invite yourself (README)."
