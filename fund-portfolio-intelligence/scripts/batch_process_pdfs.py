"""
Batch PDF Processing Script
Process multiple PDF factsheets and load into Neo4j
"""

import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.pdf_extractor import FundPortfolioProcessor
from src.database.neo4j_manager import FundPortfolioManager
from src.utils.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_pdfs_in_directory(directory: Path, output_file: str = None):
    """
    Process all PDFs in a directory
    
    Args:
        directory: Directory containing PDF files
        output_file: Optional output JSON file
    """
    # Find all PDFs
    pdf_files = list(directory.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"No PDF files found in {directory}")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Initialize processor
    processor = FundPortfolioProcessor()
    
    # Process each PDF
    all_results = {}
    
    for pdf_path in pdf_files:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {pdf_path.name}")
        logger.info(f"{'='*60}")
        
        try:
            results = processor.process_pdf(str(pdf_path))
            all_results[pdf_path.name] = results
            logger.info(f"✅ Successfully processed {pdf_path.name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {pdf_path.name}: {e}")
            continue
    
    # Save all results if output file specified
    if output_file:
        settings = get_settings()
        output_path = Path(settings.processed_data_dir) / output_file
        
        processor.cleaner.save_results(output_file)
        logger.info(f"\n💾 All results saved to: {output_path}")
    
    return all_results


def load_json_to_neo4j(json_file: Path, year: int = None, month: int = None):
    """
    Load processed JSON data into Neo4j
    
    Args:
        json_file: Path to JSON file with processed holdings
        year: Year for snapshot (defaults to current)
        month: Month for snapshot (defaults to current)
    """
    if year is None:
        year = datetime.now().year
    if month is None:
        month = datetime.now().month
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Loading data from {json_file.name} to Neo4j")
    logger.info(f"{'='*60}")
    
    # Load JSON
    with open(json_file, 'r', encoding='utf-8') as f:
        holdings_data = json.load(f)
    
    if not holdings_data:
        logger.warning("No data found in JSON file")
        return
    
    # Group by fund
    funds = {}
    for holding in holdings_data:
        fund_name = holding.get('fund_name', 'Unknown Fund')
        if fund_name not in funds:
            funds[fund_name] = []
        funds[fund_name].append(holding)
    
    logger.info(f"Found {len(funds)} funds with {len(holdings_data)} total holdings")
    
    # Load each fund
    with FundPortfolioManager() as manager:
        for fund_idx, (fund_name, fund_holdings) in enumerate(funds.items(), 1):
            logger.info(f"\n[{fund_idx}/{len(funds)}] Loading: {fund_name}")
            
            # Generate IDs
            fund_id = hash(fund_name) % (10**8)  # Generate consistent fund_id
            snapshot_id = f"{year}{month:02d}{fund_id}"
            
            # Estimate AMC from fund name (simple heuristic)
            amc = fund_name.split()[0] if fund_name else "Unknown"
            
            # Calculate total AUM (placeholder - should come from factsheet)
            total_aum = sum(h.get('weights', 0) for h in fund_holdings) * 10
            
            try:
                result = manager.load_portfolio(
                    fund_id=fund_id,
                    fund_name=fund_name,
                    amc=amc,
                    snapshot_id=snapshot_id,
                    year=year,
                    month=month,
                    total_aum=total_aum,
                    holdings_data=fund_holdings
                )
                
                logger.info(f"✅ Loaded {result['holdings_created']} holdings for {fund_name}")
                
            except Exception as e:
                logger.error(f"❌ Error loading {fund_name}: {e}")
                continue
    
    logger.info(f"\n✅ Neo4j loading complete")


def main():
    """Main batch processing function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Batch process PDF factsheets and load to Neo4j"
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        help='Directory containing PDF files (default: data/raw)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default='batch_processed_holdings.json',
        help='Output JSON filename (default: batch_processed_holdings.json)'
    )
    parser.add_argument(
        '--load-json',
        type=str,
        help='Load existing JSON file to Neo4j instead of processing PDFs'
    )
    parser.add_argument(
        '--year',
        type=int,
        help='Year for snapshot (default: current year)'
    )
    parser.add_argument(
        '--month',
        type=int,
        help='Month for snapshot (default: current month)'
    )
    
    args = parser.parse_args()
    
    settings = get_settings()
    
    if args.load_json:
        # Load existing JSON
        json_path = Path(args.load_json)
        if not json_path.exists():
            logger.error(f"JSON file not found: {json_path}")
            sys.exit(1)
        
        load_json_to_neo4j(json_path, args.year, args.month)
    
    else:
        # Process PDFs
        input_dir = Path(args.input_dir) if args.input_dir else Path(settings.raw_data_dir)
        
        if not input_dir.exists():
            logger.error(f"Input directory not found: {input_dir}")
            sys.exit(1)
        
        # Process PDFs
        results = process_pdfs_in_directory(input_dir, args.output_file)
        
        # Ask user if they want to load to Neo4j
        response = input("\n📊 Load processed data to Neo4j? (y/n): ").strip().lower()
        
        if response == 'y':
            output_path = Path(settings.processed_data_dir) / args.output_file
            if output_path.exists():
                load_json_to_neo4j(output_path, args.year, args.month)
            else:
                logger.warning(f"Output file not found: {output_path}")


if __name__ == "__main__":
    main()
