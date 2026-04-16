"""Orchestrator for the FAIRagro Middleware Harvester."""

import argparse
import asyncio
import logging
from pathlib import Path

from arctrl import ARC

from middleware.api_client import ApiClient
from middleware.harvester.config import Config
from middleware.harvester.errors import HarvesterError
from middleware.inspire.plugin import run_plugin as run_inspire_plugin

logger = logging.getLogger(__name__)

# Registry mapping plugin type names to their run_plugin functions.
# To add a new plugin: import its run_plugin and add an entry here.
_PLUGIN_RUNNERS = {
    "inspire": run_inspire_plugin,
}


async def run_orchestrator(config: Config) -> None:
    """Execute the core harvester loop across all configured repositories."""
    async with ApiClient(config.api_client) as client:
        for repo in config.repositories:
            logger.info("Initializing plugin type: %s", repo.plugin_type)

            plugin_runner = _PLUGIN_RUNNERS.get(repo.plugin_type)
            if plugin_runner is None:
                logger.error("Unknown repository type '%s', skipping...", repo.plugin_type)
                continue

            try:
                plugin_gen = plugin_runner(repo.plugin_config)

                count = 0
                async for item in plugin_gen:
                    if isinstance(item, HarvesterError):
                        logger.error("Processing error in plugin '%s': %s", repo.plugin_type, item)
                        continue

                    try:
                        # Deserialize back to ARC for the API Client
                        arc = ARC.from_rocrate_json_string(item)

                        response = await client.create_or_update_arc(
                            rdi=repo.rdi,
                            arc=arc,
                        )
                        logger.info("Successfully uploaded %s ARC ID: %s", repo.plugin_type, response.arc_id)
                        count += 1
                    except Exception as e:  # noqa: BLE001
                        logger.error("Failed to upload ARC for %s: %s", repo.plugin_type, e)

                logger.info("Finished processing repository %s with %d ARCs uploaded.", repo.plugin_type, count)
            except Exception as e:  # noqa: BLE001
                logger.error("Repository '%s' failed and will be skipped: %s", repo.plugin_type, e)


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
