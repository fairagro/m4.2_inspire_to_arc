import asyncio
import logging
import argparse
import sys
from pathlib import Path
from middleware.api_client import ApiClient, Config as ApiConfig
from .harvester import CSWClient
from .mapper import InspireMapper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def run_harvest(csw_url: str, api_config_path: Path, limit: int = 10):
    """Run the harvest process."""
    
    # 1. Setup CSW Client
    logger.info(f"Connecting to CSW at {csw_url}...")
    csw_client = CSWClient(csw_url)
    
    # 2. Setup Mapper
    mapper = InspireMapper()
    
    # 3. Setup API Client
    try:
        api_config = ApiConfig.from_yaml_file(api_config_path)
    except Exception as e:
        logger.error(f"Failed to load API config: {e}")
        return

    # 4. Harvest and Process
    async with ApiClient(api_config) as client:
        batch = []
        count = 0
        
        try:
            for record in csw_client.get_records(max_records=limit):
                logger.info(f"Processing record: {record.identifier}")
                
                try:
                    # Map to ARC
                    arc = mapper.map_record(record)
                    batch.append(arc)
                    
                    # Batch upload
                    if len(batch) >= 10:
                        logger.info(f"Uploading batch of {len(batch)} ARCs...")
                        await client.create_or_update_arcs(
                            rdi="inspire-import", # Could be configurable
                            arcs=batch
                        )
                        batch = []
                        
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to map/process record {record.identifier}: {e}")
                    continue
            
            # Upload remaining
            if batch:
                logger.info(f"Uploading final batch of {len(batch)} ARCs...")
                await client.create_or_update_arcs(
                    rdi="inspire-import",
                    arcs=batch
                )
                
            logger.info(f"Harvest complete. Processed {count} records.")
            
        except Exception as e:
            logger.error(f"Harvest failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="INSPIRE to ARC Harvester")
    parser.add_argument("--csw-url", required=True, help="URL of the CSW endpoint")
    parser.add_argument("--api-config", required=True, help="Path to API Client config.yaml")
    parser.add_argument("--limit", type=int, default=10, help="Maximum records to harvest")
    
    args = parser.parse_args()
    
    asyncio.run(run_harvest(args.csw_url, Path(args.api_config), args.limit))

if __name__ == "__main__":
    main()
