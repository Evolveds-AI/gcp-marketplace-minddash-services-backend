
gcloud builds submit --tag gcr.io/poc-suroeste/backend-service-prd-minddash:latest .

gcloud run deploy backend-service-prd-minddash \
  --image gcr.io/poc-suroeste/backend-service-prd-minddash:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 2 \