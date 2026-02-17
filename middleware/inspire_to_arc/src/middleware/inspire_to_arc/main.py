"""Main entry point for INSPIRE to ARC harvesting middleware.

This module sets up logging, parses command-line arguments, and runs the harvest process
to collect records from a CSW endpoint and upload them to an ARC API.
"""

import argparse
import asyncio
import logging
from pathlib import Path

from middleware.api_client import ApiClient
from middleware.inspire_to_arc.config import Config
from middleware.inspire_to_arc.harvester import CSWClient
from middleware.inspire_to_arc.mapper import InspireMapper

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def run_harvest(config: Config) -> None:
    """Run the harvest process."""
    # 1. Setup CSW Client
    logger.info("Connecting to CSW at %s...", config.csw_url)
    csw_client = CSWClient(config.csw_url)

    # 2. Setup Mapper
    mapper = InspireMapper()

    # 3. Harvest and Process
    async with ApiClient(config.api_client) as client:
        count = 0

        try:
            # Pass query if configured
            records_iter = csw_client.get_records(
                _query=config.query,
                xml_request=config.xml_request,
                max_records=1000000,  # Use a large number or implement proper pagination loop in main
            )

            for record in records_iter:
                logger.info("Processing record: %s", record.identifier)

                try:
                    # Map to ARC
                    arc = mapper.map_record(record)

                    # Upload ARC
                    logger.info("Uploading ARC for record %s (ARC ID: %s)", record.identifier, arc.Identifier)
                    await client.create_or_update_arc(
                        rdi=config.rdi,
                        arc=arc,
                    )

                    count += 1

                except Exception as e:  # pylint: disable=broad-exception-caught
                    record_id = getattr(record, "identifier", None) or "unknown"
                    logger.error("Failed to map/process record %s: %s", record_id, e)
                    continue

            logger.info("Harvest complete. Processed %d records.", count)

        except (RuntimeError, ValueError) as e:
            logger.error("Harvest failed: %s", e)


def main() -> None:
    """Parse command-line arguments and run the INSPIRE to ARC harvest process.

    This function sets up the argument parser, parses the arguments, and invokes
    the asynchronous harvest routine.
    """
    parser = argparse.ArgumentParser(description="INSPIRE to ARC Harvester")
    parser.add_argument("-c", "--config", required=True, type=Path, help="Path to configuration file (YAML)")

    args = parser.parse_args()

    try:
        config = Config.from_yaml_file(args.config)
    except (FileNotFoundError, ValueError) as e:
        logger.error("Failed to load configuration: %s", e)
        return

    asyncio.run(run_harvest(config))


if __name__ == "__main__":
    main()
