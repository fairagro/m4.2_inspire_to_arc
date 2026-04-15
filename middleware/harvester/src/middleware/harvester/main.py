"""Orchestrator for the FAIRagro Middleware Harvester."""

import argparse
import asyncio
import logging
from pathlib import Path

from arctrl import ARC

from middleware.api_client import ApiClient
from middleware.harvester.config import Config
from middleware.inspire_to_arc.plugin import run_plugin

logger = logging.getLogger(__name__)


async def run_orchestrator(config: Config) -> None:
    """Execute the core harvester loop across all configured repositories."""
    async with ApiClient(config.api_client) as client:
        for repo in config.repositories:
            logger.info("Initializing plugin type: %s", repo.plugin_type)

            if repo.plugin_type == "inspire":
                plugin_config = repo.plugin_config
                plugin_gen = run_plugin(plugin_config)
            else:
                logger.error("Unknown repository type '%s', skipping...", repo.plugin_type)
                continue

            count = 0
            async for arc_json in plugin_gen:
                try:
                    # Deserialize back to ARC for the API Client
                    arc = ARC.from_rocrate_json_string(arc_json)

                    response = await client.create_or_update_arc(
                        rdi=plugin_config.rdi,
                        arc=arc,
                    )
                    logger.info("Successfully uploaded %s ARC ID: %s", repo.plugin_type, response.arc_id)
                    count += 1
                except Exception as e:  # noqa: BLE001
                    logger.error("Failed to upload ARC for %s: %s", repo.plugin_type, e)

            logger.info("Finished processing repository %s with %d ARCs uploaded.", repo.plugin_type, count)


def main() -> None:
    """CLI entry point for the Middleware Harvester."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="FAIRagro Middleware Harvester Orchestrator")
    parser.add_argument("-c", "--config", required=True, type=Path, help="Path to config file")

    args = parser.parse_args()

    try:
        config = Config.from_yaml_file(args.config)
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to load root configuration: %s", e)
        return

    asyncio.run(run_orchestrator(config))


if __name__ == "__main__":
    main()
