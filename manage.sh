#!/bin/bash
# Helper script for managing email-to-slack Cloud Run Job
# Usage: ./manage.sh [command]

set -e

# Configuration
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
JOB_NAME="${JOB_NAME:-email-to-slack-job}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

function show_help() {
  cat << EOF
Email to Slack - Management Script

Usage: ./manage.sh [command]

Commands:
  logs              View recent logs
  tail              Follow logs in real-time
  execute           Run the job manually
  executions        List recent job executions
  status            Show job status
  scheduler-status  Show scheduler status
  scheduler-run     Trigger scheduler manually
  scheduler-pause   Pause the scheduler
  scheduler-resume  Resume the scheduler
  update-env        Update environment variables
  help              Show this help message

Environment Variables:
  PROJECT_ID        GCP Project ID (default: current gcloud project)
  REGION            GCP Region (default: us-central1)
  JOB_NAME          Cloud Run Job name (default: email-to-slack-job)

Examples:
  ./manage.sh logs
  ./manage.sh execute
  PROJECT_ID=my-project ./manage.sh status
EOF
}

function check_config() {
  if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID not set. Set it with: export PROJECT_ID=your-project-id"
    exit 1
  fi
}

case "${1:-help}" in
  logs)
    check_config
    echo -e "${GREEN}Fetching recent logs...${NC}"
    gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}" \
      --limit=50 \
      --project=${PROJECT_ID} \
      --format="table(timestamp,severity,textPayload)"
    ;;
    
  tail)
    check_config
    echo -e "${GREEN}Following logs (Ctrl+C to exit)...${NC}"
    gcloud logging tail "resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}" \
      --project=${PROJECT_ID}
    ;;
    
  execute)
    check_config
    echo -e "${GREEN}Executing job manually...${NC}"
    gcloud run jobs execute ${JOB_NAME} \
      --region=${REGION} \
      --project=${PROJECT_ID}
    ;;
    
  executions)
    check_config
    echo -e "${GREEN}Recent job executions:${NC}"
    gcloud run jobs executions list \
      --job=${JOB_NAME} \
      --region=${REGION} \
      --project=${PROJECT_ID} \
      --limit=10
    ;;
    
  status)
    check_config
    echo -e "${GREEN}Job status:${NC}"
    gcloud run jobs describe ${JOB_NAME} \
      --region=${REGION} \
      --project=${PROJECT_ID}
    ;;
    
  scheduler-status)
    check_config
    echo -e "${GREEN}Scheduler status:${NC}"
    gcloud scheduler jobs describe email-to-slack-scheduler \
      --location=${REGION} \
      --project=${PROJECT_ID}
    ;;
    
  scheduler-run)
    check_config
    echo -e "${GREEN}Triggering scheduler manually...${NC}"
    gcloud scheduler jobs run email-to-slack-scheduler \
      --location=${REGION} \
      --project=${PROJECT_ID}
    ;;
    
  scheduler-pause)
    check_config
    echo -e "${YELLOW}Pausing scheduler...${NC}"
    gcloud scheduler jobs pause email-to-slack-scheduler \
      --location=${REGION} \
      --project=${PROJECT_ID}
    echo -e "${GREEN}Scheduler paused${NC}"
    ;;
    
  scheduler-resume)
    check_config
    echo -e "${GREEN}Resuming scheduler...${NC}"
    gcloud scheduler jobs resume email-to-slack-scheduler \
      --location=${REGION} \
      --project=${PROJECT_ID}
    echo -e "${GREEN}Scheduler resumed${NC}"
    ;;
    
  update-env)
    check_config
    echo -e "${YELLOW}Update environment variables${NC}"
    echo "Enter values (press Enter to skip):"
    read -p "IMAP_PASSWORD: " IMAP_PASSWORD
    read -p "SLACK_BOT_TOKEN: " SLACK_BOT_TOKEN
    
    ENV_VARS=""
    if [ -n "$IMAP_PASSWORD" ]; then
      ENV_VARS="IMAP_PASSWORD=${IMAP_PASSWORD}"
    fi
    if [ -n "$SLACK_BOT_TOKEN" ]; then
      if [ -n "$ENV_VARS" ]; then
        ENV_VARS="${ENV_VARS},SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}"
      else
        ENV_VARS="SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}"
      fi
    fi
    
    if [ -n "$ENV_VARS" ]; then
      echo -e "${GREEN}Updating environment variables...${NC}"
      gcloud run jobs update ${JOB_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --set-env-vars="${ENV_VARS}"
      echo -e "${GREEN}Environment variables updated${NC}"
    else
      echo "No variables to update"
    fi
    ;;
    
  help|*)
    show_help
    ;;
esac
