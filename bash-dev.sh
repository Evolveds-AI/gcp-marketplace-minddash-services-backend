
gcloud builds submit --tag gcr.io/poc-suroeste/backend-service-dev-minddash:latest .

gcloud run deploy backend-service-dev-minddash \
  --image gcr.io/poc-suroeste/backend-service-dev-minddash:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 2 \
  --min-instances 0