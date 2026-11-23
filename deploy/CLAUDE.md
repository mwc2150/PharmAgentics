@README.md

# deploy rules

- A merge to `main` deploys the app to Cloud Run once CI passes (`.github/workflows/deploy-uat.yml`). Keycloak is deployed by hand.
- Secrets live only in the git-ignored `.env`. Never commit keys. `deploy/gcp.py anthropic-key` stores the Anthropic key for Cloud Run.
- The GCP budget is $0: stay on free tiers.
- `deploy/demo-credentials.env` holds shared demo passwords for the role logins. Nothing else secret goes in the repo.
