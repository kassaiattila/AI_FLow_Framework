"""Email Connector service — configurable multi-provider email fetching."""

from aiflow.services.email_connector.service import (
    ConnectorProvider,
    EmailConnectorConfig,
    EmailConnectorService,
    FetchedEmail,
    FetchResult,
)

__all__ = [
    "ConnectorProvider",
    "EmailConnectorConfig",
    "EmailConnectorService",
    "FetchedEmail",
    "FetchResult",
]
