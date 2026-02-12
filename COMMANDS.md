# Quick Reference - GCP Cloud Run Job Commands

## Environment Setup
```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
export JOB_NAME="email-to-slack-job"
```

## Deployment

### First Time - Create Job
```bash
gcloud run jobs create ${JOB_NAME} \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/email-to-slack/job:latest \
  --region=${REGION} \
  --set-env-vars="IMAP_HOST=imap.mail.yahoo.com" \
  --set-env-vars="IMAP_PORT=993" \
  --set-env-vars="IMAP_USERNAME=your-email@yahoo.com" \
  --set-env-vars="IMAP_PASSWORD=your-app-password" \
  --set-env-vars="IMAP_ALLOWED_FROM=noreply@sandiego.gov" \
  --set-env-vars="SLACK_BOT_TOKEN=xoxb-your-token" \
  --memory=512Mi \
  --cpu=1 \
  --task-timeout=300 \
  --max-retries=1
```

### Update Code (Redeploy)
```bash
# Build and push new image
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/email-to-slack/job:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/email-to-slack/job:latest

# Update job
gcloud run jobs update ${JOB_NAME} \
  --region=${REGION} \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/email-to-slack/job:latest
```

### Update Environment Variables Only
```bash
gcloud run jobs update ${JOB_NAME} \
  --region=${REGION} \
  --set-env-vars="IMAP_PASSWORD=new-password,SLACK_BOT_TOKEN=new-token"
```

## Testing & Monitoring

### Execute Job Manually
```bash
gcloud run jobs execute ${JOB_NAME} --region=${REGION}
```

### View Recent Logs
```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}" \
  --limit=50 \
  --format="table(timestamp,severity,textPayload)"
```

### Follow Logs in Real-time
```bash
gcloud logging tail "resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}"
```

### List Job Executions
```bash
gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION}
```

### Describe Job Configuration
```bash
gcloud run jobs describe ${JOB_NAME} --region=${REGION}
```

## Cloud Scheduler

### Create Scheduler (Every 5 Minutes)
```bash
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
export SCHEDULER_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com

gcloud scheduler jobs create http email-to-slack-scheduler \
  --location=${REGION} \
  --schedule="*/5 * * * *" \
  --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
  --http-method=POST \
  --oauth-service-account-email=${SCHEDULER_SA}
```

### Test Scheduler Manually
```bash
gcloud scheduler jobs run email-to-slack-scheduler --location=${REGION}
```

### List Schedulers
```bash
gcloud scheduler jobs list --location=${REGION}
```

### Pause Scheduler
```bash
gcloud scheduler jobs pause email-to-slack-scheduler --location=${REGION}
```

### Resume Scheduler
```bash
gcloud scheduler jobs resume email-to-slack-scheduler --location=${REGION}
```

### Update Schedule
```bash
# Every 10 minutes instead of 5
gcloud scheduler jobs update http email-to-slack-scheduler \
  --location=${REGION} \
  --schedule="*/10 * * * *"
```

## Troubleshooting

### Check Job Status
```bash
gcloud run jobs describe ${JOB_NAME} --region=${REGION} --format="value(status.conditions)"
```

### View Latest Execution Logs
```bash
EXECUTION=$(gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION} --limit=1 --format="value(name)")
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME} AND labels.run.googleapis.com/execution_name=${EXECUTION}" --limit=100
```

### Check IAM Permissions
```bash
gcloud run jobs get-iam-policy ${JOB_NAME} --region=${REGION}
```

## Resource Management

### Increase Memory/CPU
```bash
gcloud run jobs update ${JOB_NAME} \
  --region=${REGION} \
  --memory=1Gi \
  --cpu=2
```

### Increase Timeout
```bash
gcloud run jobs update ${JOB_NAME} \
  --region=${REGION} \
  --task-timeout=600
```

## Cleanup

### Delete Job
```bash
gcloud run jobs delete ${JOB_NAME} --region=${REGION}
```

### Delete Scheduler
```bash
gcloud scheduler jobs delete email-to-slack-scheduler --location=${REGION}
```

### Delete Artifact Registry Repository
```bash
gcloud artifacts repositories delete email-to-slack --location=${REGION}
```

## Schedule Syntax Examples

```bash
# Every 5 minutes
--schedule="*/5 * * * *"

# Every 10 minutes
--schedule="*/10 * * * *"

# Every hour
--schedule="0 * * * *"

# Every 2 hours
--schedule="0 */2 * * *"

# Every day at 9 AM
--schedule="0 9 * * *"

# Every weekday at 9 AM
--schedule="0 9 * * 1-5"

# Every Monday at 9 AM
--schedule="0 9 * * 1"
```

Format: `minute hour day-of-month month day-of-week`
- minute: 0-59
- hour: 0-23
- day-of-month: 1-31
- month: 1-12
- day-of-week: 0-7 (0 and 7 are Sunday)
