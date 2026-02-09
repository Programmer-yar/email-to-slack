#!/bin/bash
# Quick deployment script for email-to-slack Cloud Run Job
# Usage: ./deploy.sh
#
# This script automates the entire deployment pipeline:
# 1. Verifies dependencies (gcloud, docker)
# 2. Enables required GCP APIs
# 3. Creates Artifact Registry repository
# 4. Builds and pushes Docker image
# 5. Creates/updates Cloud Run Job
# 6. Sets up Cloud Scheduler for automated runs

# Exit immediately if any command fails
set -e

# Colors for pretty terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Email to Slack - GCP Cloud Run Job Deployment ===${NC}\n"

# Verify that gcloud CLI and Docker are installed before proceeding
for cmd in gcloud docker; do
  if ! command -v $cmd &> /dev/null; then
    echo -e "${RED}Error: $cmd is not installed${NC}"
    exit 1
  fi
done

# Configuration - Can be overridden by setting environment variables before running this script
# Example: PROJECT_ID=my-project REGION=us-east1 ./deploy.sh
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"  # Use env var or gcloud default
REGION="${REGION:-us-central1}"                                            # Default to us-central1
IMAGE_NAME="${IMAGE_NAME:-email-to-slack}"                                 # Docker image name
JOB_NAME="${JOB_NAME:-email-to-slack-job}"                                 # Cloud Run Job name

# Prompt for project ID if not set in environment or gcloud config
if [ -z "$PROJECT_ID" ]; then
  read -p "Enter your GCP Project ID: " PROJECT_ID
fi

# Display configuration and wait for user confirmation
echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Image Name: $IMAGE_NAME"
echo "  Job Name: $JOB_NAME"
echo ""

read -p "Continue with deployment? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Deployment cancelled"
  exit 0
fi

# ============================================================================
# STEP 1/8: Set the active GCP project
# ============================================================================
echo -e "\n${GREEN}[1/8] Setting GCP project...${NC}"
gcloud config set project ${PROJECT_ID}

# Get project number (needed later for service account configuration)
export PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
echo "  Project Number: $PROJECT_NUMBER"

# ============================================================================
# STEP 2/8: Enable required GCP services/APIs
# ============================================================================
echo -e "\n${GREEN}[2/8] Enabling required GCP APIs...${NC}"
gcloud services enable \
  run.googleapis.com \                # Cloud Run - to run containerized jobs
  cloudbuild.googleapis.com \         # Cloud Build - for building containers
  cloudscheduler.googleapis.com \     # Cloud Scheduler - for automated scheduling
  artifactregistry.googleapis.com     # Artifact Registry - for storing Docker images

# ============================================================================
# STEP 3/8: Create Artifact Registry repository to store Docker images
# ============================================================================
echo -e "\n${GREEN}[3/8] Creating Artifact Registry repository...${NC}"
if gcloud artifacts repositories describe ${IMAGE_NAME} --location=${REGION} &>/dev/null; then
  echo "  Repository already exists, skipping..."
else
  gcloud artifacts repositories create ${IMAGE_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Email to Slack application"
fi

# ============================================================================
# STEP 4/8: Configure Docker to authenticate with Google Artifact Registry
# ============================================================================
echo -e "\n${GREEN}[4/8] Configuring Docker authentication...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# ============================================================================
# STEP 5/8: Build Docker image for Cloud Run (requires linux/amd64 platform)
# ============================================================================
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${IMAGE_NAME}/job:latest"
echo -e "\n${GREEN}[5/8] Building Docker image for linux/amd64...${NC}"
# Platform must be linux/amd64 for Cloud Run compatibility
docker build --platform linux/amd64 -t ${IMAGE_URI} .

# ============================================================================
# STEP 6/8: Push the built image to Artifact Registry
# ============================================================================
echo -e "\n${GREEN}[6/8] Pushing image to Artifact Registry...${NC}"
docker push ${IMAGE_URI}

# Check if the Cloud Run Job already exists (determines next steps)
JOB_EXISTS=$(gcloud run jobs describe ${JOB_NAME} --region=${REGION} 2>/dev/null && echo "true" || echo "false")

# ============================================================================
# CONDITIONAL: Job doesn't exist yet - Display creation command
# ============================================================================
if [ "$JOB_EXISTS" = "false" ]; then
  echo -e "\n${YELLOW}Job does not exist. You need to create it with environment variables.${NC}"
  echo -e "${YELLOW}Run the following command with your actual credentials:${NC}\n"
  
  # Display the command template with placeholder values
  # User must replace these with their actual credentials
  cat << EOF
gcloud run jobs create ${JOB_NAME} \\
  --image=${IMAGE_URI} \\
  --region=${REGION} \\
  --set-env-vars="IMAP_HOST=imap.mail.yahoo.com" \\
  --set-env-vars="IMAP_PORT=993" \\
  --set-env-vars="IMAP_USERNAME=your-email@yahoo.com" \\
  --set-env-vars="IMAP_PASSWORD=your-app-password" \\
  --set-env-vars="IMAP_ALLOWED_FROM=noreply@sandiego.gov,ahmadyar228@gmail.com" \\
  --set-env-vars="SLACK_BOT_TOKEN=xoxb-your-slack-bot-token" \\
  --memory=512Mi \\
  --cpu=1 \\
  --task-timeout=300 \\
  --max-retries=1
EOF
  
  echo -e "\n${YELLOW}After creating the job, run this script again to set up the scheduler.${NC}"
  exit 0

# ============================================================================
# CONDITIONAL: Job exists - Update it and set up scheduler
# ============================================================================
else
  # ============================================================================
  # STEP 7/8: Update the existing Cloud Run Job with the new image
  # ============================================================================
  echo -e "\n${GREEN}[7/8] Updating existing Cloud Run Job...${NC}"
  gcloud run jobs update ${JOB_NAME} \
    --region=${REGION} \
    --image=${IMAGE_URI}
  
  # ============================================================================
  # STEP 8/8: Set up Cloud Scheduler for automated runs
  # ============================================================================
  echo -e "\n${GREEN}[8/8] Setting up Cloud Scheduler...${NC}"
  
  # Use the default compute service account for Cloud Scheduler
  SCHEDULER_SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
  
  # Grant the service account permission to invoke the Cloud Run Job
  gcloud run jobs add-iam-policy-binding ${JOB_NAME} \
    --region=${REGION} \
    --member="serviceAccount:${SCHEDULER_SA}" \
    --role="roles/run.invoker" \
    --quiet 2>/dev/null || true
  
  # Create Cloud Scheduler job if it doesn't exist
  # This will trigger the job every 5 minutes (*/5 * * * *)
  if gcloud scheduler jobs describe email-to-slack-scheduler --location=${REGION} &>/dev/null; then
    echo "  Scheduler job already exists, skipping..."
  else
    gcloud scheduler jobs create http email-to-slack-scheduler \
      --location=${REGION} \
      --schedule="*/5 * * * *" \
      --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
      --http-method=POST \
      --oauth-service-account-email=${SCHEDULER_SA}
  fi
fi

# ============================================================================
# Deployment complete - Display helpful next steps
# ============================================================================
echo -e "\n${GREEN}=== Deployment Complete ===${NC}\n"
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test manually: gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo "  2. View logs: gcloud logging read \"resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}\" --limit=50"
echo "  3. Test scheduler: gcloud scheduler jobs run email-to-slack-scheduler --location=${REGION}"
echo ""
echo -e "${GREEN}Job will run every 5 minutes automatically via Cloud Scheduler${NC}"
