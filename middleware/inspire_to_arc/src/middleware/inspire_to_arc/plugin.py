"""Plugin generator for INSPIRE-to-ARC harvesting.

Exposes `run_plugin`, the `AsyncGenerator` integration point consumed by the
central Harvester orchestrator. This module contains no CLI entry point.
"""

import logging
from collections.abc import AsyncGenerator

from middleware.inspire_to_arc.config import Config
from middleware.inspire_to_arc.csw_client import CSWClient
from middleware.inspire_to_arc.errors import RecordProcessingError
from middleware.inspire_to_arc.mapper import InspireMapper

logger = logging.getLogger(__name__)


async def run_plugin(config: Config) -> AsyncGenerator[str, None]:
    """Run the harvest process and yield serialized RO-Crate ARCs."""
    # 1. Setup CSW Client
    logger.info("Connecting to CSW at %s...", config.csw_url)
    csw_client = CSWClient(config.csw_url)

    # 2. Setup Mapper
    mapper = InspireMapper()

    # 3. Harvest and Process
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

            # Skip non-dataset records (e.g., services)
            if record.hierarchy and record.hierarchy.lower() not in ["dataset", "series", "nongeographicdataset"]:
                logger.info("Skipping non-dataset record %s (Type: %s)", record.identifier, record.hierarchy)
                continue

            # Log the INSPIRE identifier (UUID)
            logger.debug("Processing record %s (URL: %s)", record.identifier, record_url)

            try:
                # Map to ARC
                arc = mapper.map_record(record)

                # Yield serialized ARC
                json_str = arc.ToROCrateJsonString()
                yield json_str

                logger.info("Successfully generated ARC for record %s - URL: %s", record.identifier, record_url)
                count += 1

            except Exception as e:  # noqa: BLE001
                logger.error("Failed to map/upload record %s: %s (URL: %s)", record.identifier, e, record_url)
                continue

        logger.info("Harvest generator exhausted. Processed %d records.", count)

    except (RuntimeError, ValueError) as e:
        logger.error("Harvest failed: %s", e)
