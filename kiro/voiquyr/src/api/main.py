"""
Main FastAPI Application Entry Point

Starts the EUVoice AI Platform API server.
"""

import uvicorn
import logging
from .app import create_app
from .config import APIConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the API server."""
    config = APIConfig()
    app = create_app(config)
    
    logger.info(f"Starting EUVoice AI Platform API on {config.host}:{config.port}")
    logger.info(f"Environment: {config.environment}")
    logger.info(f"EU Data Residency: {config.eu_data_residency}")
    logger.info(f"GDPR Mode: {config.gdpr_mode}")
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.port,
        log_level=config.log_level.lower(),
        access_log=True,
        reload=config.is_development
    )


if __name__ == "__main__":
    main()