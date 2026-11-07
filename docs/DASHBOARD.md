# The dashboard (Channel Studio): your channels on one private web page

A small web app you deploy into **your own AWS account**. Only the email addresses you allow can sign in.

| Page | What it shows |
|---|---|
| Overview | every channel: subscribers, views and watch hours (28 days, with change), net subscribers, a trend line |
| Channel | views and watch time (90 days), subscribers gained/lost, traffic sources, the YouTube searches that found it, top videos with average % viewed, scheduled releases, recent uploads |
| Rotation | a pause switch, the calendar, each day's topics and videos (queued / failed with the reason), your topic choices |
| Keywords | Keyword Planner research in the browser; **Use next** / **Never** per channel, read by the rotation |
| Search Console | a card per property; click for daily clicks and impressions, top queries, pages and countries |

Data is collected once a day (05:15 UTC) and on demand ("refresh now"). Revenue is not shown (it needs the
`yt-analytics-monetary.readonly` scope; add it yourself if your channels are monetised).

## What it is made of (about $0 a month at personal scale)

CloudFront + a private S3 bucket for the page, one Lambda behind CloudFront (Origin Access Control), DynamoDB on demand,
a Cognito user pool where users can only be invited, an EventBridge rule for the daily collection, and SSM Parameter
Store (encrypted) for your keys. All in one CloudFormation stack (`dashboard/infra/template.yaml`).

## Deploy

You need: an AWS account and the AWS CLI signed in (`aws sts get-caller-identity` works), Python 3.10+ with pip, `zip`.

```bash
cd channel-autopilot
STACK=chstudio AUTH_PREFIX=mychannels-studio ALLOWED=you@example.com ./dashboard/deploy.sh
```

- `AUTH_PREFIX` must be globally unique (it becomes `<prefix>.auth.<region>.amazoncognito.com`, the sign-in page).
- `ALLOWED`: comma-separated emails that may sign in, even if someone else were invited by mistake.
- Region: `us-east-1` by default (`AWS_REGION` to change).
- It prints the address: `https://dxxxxxxxx.cloudfront.net/`.

## Give it your keys

```bash
# once: the service account (Search Console + Keyword Planner) and the Google Ads customer id
python3 dashboard/setup_keys.py ../secrets/google-sa.json 123-456-7890
#   → prints a rotation token: save it, e.g. to ~/secrets/studio-token (chmod 600)

# per channel: id = the channel's folder name in your rotation, a display name, its YouTube token
python3 dashboard/add_channel.py tech-channel "Tech Channel" ../tech-channel/secrets/youtube-token.json
```

The YouTube token must come from a sign-in that included the analytics scope. Tokens made by `autopilot youtube-auth`
before version 0.2 lack it: run `youtube-auth` again for that channel.

## Invite yourself

```bash
POOL=$(aws cloudformation describe-stacks --stack-name chstudio --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" --output text)
aws cognito-idp admin-create-user --user-pool-id $POOL --username you@example.com \
  --user-attributes Name=email,Value=you@example.com Name=email_verified,Value=true --desired-delivery-mediums EMAIL
```

You get an email with a temporary password. Open the dashboard, sign in, set your own password. Collect data once:

```bash
aws lambda invoke --function-name chstudio-api --payload '{"collect":"all"}' --cli-binary-format raw-in-base64-out out.json
```

## Your own domain (optional)

1. Request a certificate for e.g. `studio.example.com` in **AWS Certificate Manager, us-east-1**, DNS validation; add the
   validation record at your DNS host and wait until it is **Issued**.
2. Redeploy with it: `CERT_ARN=arn:aws:acm:us-east-1:...:certificate/... ALIAS=studio.example.com STACK=... AUTH_PREFIX=... ALLOWED=... ./dashboard/deploy.sh`
3. At your DNS host, point `studio` at the CloudFront domain (CNAME; or an alias A/AAAA record in Route 53).

## Connect the rotation

In `rotation.yml`: `dashboard: {url: "https://studio.example.com", token_file: "~/secrets/studio-token"}`.

## Security notes

- Your keys stay in **your** SSM Parameter Store (`/chstudio/*`, encrypted); only the dashboard's Lambda role can read them.
- The browser sends a Cognito ID token; the Lambda verifies its signature, audience and expiry, and the email against
  `ALLOWED`. The rotation's calls use a separate random token.
- Self sign-up is off; you invite users. Turn on MFA (TOTP) per user in the Cognito console if you like.
- Delete everything: `aws cloudformation delete-stack --stack-name chstudio`, then the SSM parameters under `/chstudio/`
  and the code bucket `chstudio-code-<account>`.
