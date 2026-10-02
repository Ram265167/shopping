from app.core.config import settings

# Database wiring will use DATABASE_URL in the next backend phase.
# Keep credentials in environment variables; never commit secrets.
DATABASE_URL = settings.database_url
