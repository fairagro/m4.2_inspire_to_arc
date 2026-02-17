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
from middleware.inspire_to_arc.errors import RecordProcessingError
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

            for item in records_iter:
                # Handle potential processing errors emitted by the harvester
                if isinstance(item, RecordProcessingError):
                    record_id = item.record_id
                    record_url = csw_client.get_record_url(record_id)
                    logger.error(
                        "Failed to parse/fetch record %s: %s (URL: %s)",
                        record_id,
                        item.original_error or item,
                        record_url,
                    )
                    continue

                record = item
                record_url = csw_client.get_record_url(record.identifier)

                # Log the INSPIRE identifier (UUID)
                logger.debug("Processing record %s (URL: %s)", record.identifier, record_url)

                try:
                    # Map to ARC
                    arc = mapper.map_record(record)

                    # Upload ARC
                    logger.debug("Uploading ARC for record: %s", record.identifier)
                    response = await client.create_or_update_arc(
                        rdi=config.rdi,
                        arc=arc,
                    )

                    arc_id = response.arc.id if hasattr(response, "arc") and hasattr(response.arc, "id") else response
                    logger.info(
                        "Successfully uploaded record %s (ARC ID: %s) - URL: %s", record.identifier, arc_id, record_url
                    )
                    count += 1

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Failed to map/upload record %s: %s (URL: %s)", record.identifier, e, record_url)
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
