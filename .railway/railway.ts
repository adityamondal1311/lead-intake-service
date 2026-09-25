/**
 * Railway Infrastructure as Code for the Lead Intake Service.
 *
 * Evaluated by the Railway CLI, not on git push:
 *   railway config plan    # diff this file against the linked Railway environment
 *   railway config apply   # apply the reviewed diff
 *
 * The Dockerfiles stay the source of truth for how each image is built (the same ones the CI
 * `docker` job builds and smoke-tests); this file only says how Railway runs them.
 *
 * No secret values live here: META_APP_SECRET and META_VERIFY_TOKEN are set in Railway directly
 * and `preserve()` tells IaC to keep whatever value Railway holds.
 */
import { defineRailway, github, postgres, preserve, project, service } from 'railway/iac'

const REPO = 'adityamondal1311/lead-intake-service'

export default defineRailway(() => {
  // Managed PostgreSQL. No public domain or TCP proxy: reachable only on the private network.
  const db = postgres('Postgres')

  const backend = service('backend', {
    // checkSuites: Railway's "Wait for CI": deploy only once GitHub Actions has passed.
    source: github(REPO, { branch: 'main', rootDirectory: 'backend', checkSuites: true }),
    build: {
      builder: 'DOCKERFILE', // backend/Dockerfile
      watchPatterns: ['/backend/**'], // a frontend-only change does not redeploy the backend
    },
    deploy: {
      // Release step: runs once per deploy in the new image, before it takes traffic. A failed
      // migration fails the deploy and the previous version keeps serving.
      preDeployCommand: ['alembic upgrade head'],
      // Traffic moves only once the new container answers /health (which checks PostgreSQL).
      healthcheckPath: '/health',
      healthcheckTimeout: 120,
      restartPolicyType: 'ON_FAILURE',
      restartPolicyMaxRetries: 5,
    },
    env: {
      ENVIRONMENT: 'production', // refuses to start without the two secrets below
      LOG_LEVEL: 'INFO',
      // Migrations are the release step above, not a per-replica start-up action.
      RUN_MIGRATIONS_ON_START: 'false',
      // Private-network URL (postgresql://…; the app pins the psycopg driver itself).
      DATABASE_URL: db.env.DATABASE_URL,
      // Only the deployed dashboard may call the API from a browser.
      CORS_ORIGINS: '["https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}"]',
      META_APP_SECRET: preserve(),
      META_VERIFY_TOKEN: preserve(),
    },
  })

  const frontend = service('frontend', {
    source: github(REPO, { branch: 'main', rootDirectory: 'frontend', checkSuites: true }),
    build: {
      builder: 'DOCKERFILE', // frontend/Dockerfile
      watchPatterns: ['/frontend/**'],
    },
    deploy: {
      healthcheckPath: '/',
      healthcheckTimeout: 60,
      restartPolicyType: 'ON_FAILURE',
      restartPolicyMaxRetries: 5,
    },
    env: {
      // Passed to the Docker build (the Dockerfile declares ARG VITE_API_BASE_URL) and compiled
      // into the bundle: the browser calls the backend's public HTTPS domain.
      VITE_API_BASE_URL: 'https://${{backend.RAILWAY_PUBLIC_DOMAIN}}',
    },
  })

  return project('lead-intake-service', { resources: [db, backend, frontend] })
})
