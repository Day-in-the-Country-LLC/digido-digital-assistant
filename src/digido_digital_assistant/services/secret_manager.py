import logging
import os

from google.cloud import secretmanager

from digido_digital_assistant.config import settings

logger = logging.getLogger(__name__)


def get_secret(secret_id: str, version_id: str = "latest") -> str | None:
    project_id = settings.gcp_project_id or os.environ.get("GCP_PROJECT_ID", "")
    if not project_id:
        logger.warning("GCP project ID not configured; cannot read secret %s.", secret_id)
        return None

    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        logger.exception("Failed to fetch secret %s: %s", secret_id, exc)
        return None
