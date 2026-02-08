# Deploying on GCP (every 5 minutes + simple state)

Recommended setup:

- **Schedule**: Cloud Scheduler → Cloud Run Job (runs every 5 minutes).
- **State**: One object in **Cloud Storage** for the last UID (no database).

## Cost estimate (approximate, USD/month)

Assumptions: job runs every 5 minutes (≈8,640 runs/month), 1 vCPU, 512 MiB RAM, region `us-central1`. Cloud Run Jobs bill **per run with a 1-minute minimum** even if the script finishes in seconds.

| Component        | Usage                         | Free tier              | Estimated cost   |
|-----------------|-------------------------------|------------------------|------------------|
| **Cloud Run Job** | 8,640 runs × 1 min = 518,400 vCPU-sec, 259,200 GiB-sec | 240,000 vCPU-sec, 450,000 GiB-sec | **~$5** (vCPU over free tier; memory within free tier) |
| **Cloud Scheduler** | 1 job                        | 3 jobs free            | **$0**           |
| **Cloud Storage** | 1 small object + read/write per run | 5 GB storage, 5k Class A ops | **$0** (negligible) |

**Rough total: ~\$5/month** (often less if the job finishes quickly and you stay within free tier in some months). Prices from [Cloud Run pricing](https://cloud.google.com/run/pricing); check your region and [calculator](https://cloud.google.com/products/calculator) for exact numbers.

## 1. Prerequisites

- `gcloud` CLI installed and logged in.
- A GCP project with billing enabled.

## 2. Create a GCS bucket for state

```bash
export PROJECT_ID=your-gcp-project
export REGION=us-central1
export BUCKET=your-project-email-to-slack-state

gcloud storage buckets create gs://${BUCKET} --project=${PROJECT_ID} --location=${REGION}
```

Create the state object path (optional; the app will create it on first write):

```bash
# Optional: create empty object so the path exists
echo -n "" | gcloud storage cp - gs://${BUCKET}/state/last_email_uid
```

## 3. Build and deploy the Cloud Run Job

```bash
# Build the image (Artifact Registry)
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
export IMAGE=${REGION}-docker.pkg.dev/${PROJECT_ID}/email-to-slack/job:latest

docker build -t ${IMAGE} .
docker push ${IMAGE}
```

Create the job (no HTTP port; it runs once and exits):

```bash
gcloud run jobs create email-to-slack-job \
  --image=${IMAGE} \
  --region=${REGION} \
  --project=${PROJECT_ID} \
  --set-env-vars="IMAP_HOST=imap.mail.yahoo.com" \
  --set-env-vars="IMAP_USERNAME=your-email@yahoo.com" \
  --set-env-vars="IMAP_PASSWORD=your-app-password" \
  --set-env-vars="IMAP_ALLOWED_FROM=noreply@sandiego.gov,ahmadyar228@gmail.com" \
  --set-env-vars="SLACK_BOT_TOKEN=xoxb-your-slack-token" \
  --memory=512Mi \
  --cpu=1 \
  --task-timeout=300 \
  --max-retries=0
```

**Secrets (recommended for production):** store `IMAP_PASSWORD` and `SLACK_BOT_TOKEN` in Secret Manager and reference them:

```bash
# Create secrets first, then:
gcloud run jobs update email-to-slack-job \
  --region=${REGION} \
  --set-secrets="IMAP_PASSWORD=imap-password:latest,SLACK_BOT_TOKEN=slack-token:latest"
```

Grant the job’s service account access to GCS and (if used) Secret Manager:

```bash
export SA=$(gcloud run jobs describe email-to-slack-job --region=${REGION} --format='value(spec.template.spec.serviceAccountName)')
# If SA is empty, use the default compute SA
export SA=${SA:-${PROJECT_ID}@${PROJECT_ID}.iam.gserviceaccount.com}

gcloud storage buckets add-iam-policy-binding gs://${BUCKET} \
  --member="serviceAccount:${SA}" \
  --role="roles/storage.objectAdmin"
```

## 4. Run every 5 minutes with Cloud Scheduler

Use the **Run v2 API** to execute the job. The scheduler’s service account needs **Cloud Run Invoker** on the job.

```bash
# Use the default compute SA or a dedicated SA with roles/run.invoker
export SCHEDULER_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com

gcloud run jobs add-iam-policy-binding email-to-slack-job \
  --region=${REGION} \
  --member="serviceAccount:${SCHEDULER_SA}" \
  --role="roles/run.invoker" \
  --project=${PROJECT_ID}

gcloud scheduler jobs create http email-to-slack-every-5min \
  --location=${REGION} \
  --schedule="*/5 * * * *" \
  --uri="https://run.googleapis.com/v2/projects/${PROJECT_ID}/locations/${REGION}/jobs/email-to-slack-job:run" \
  --http-method=POST \
  --oauth-service-account-email=${SCHEDULER_SA} \
  --project=${PROJECT_ID}
```

Replace `PROJECT_NUMBER` with your project number (`gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)'`).

## 5. Summary

| Requirement        | Solution                |
|--------------------|-------------------------|
| Run every 5 minutes | Cloud Scheduler → Cloud Run Job |
| Avoid re-processing | Emails are marked as \Seen after fetch; next run only sees new UNSEEN mail. No external state needed. |

## 6. Manual test

```bash
gcloud run jobs execute email-to-slack-job --region=${REGION} --project=${PROJECT_ID}
```

Then check logs in Cloud Console → Cloud Run → Jobs → email-to-slack-job → Logs.
