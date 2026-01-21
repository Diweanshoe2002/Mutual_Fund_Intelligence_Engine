"""
Database Setup Script
Initializes databases and creates necessary schemas
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import get_settings, get_neo4j_config, get_database_config
from src.database.neo4j_manager import FundPortfolioManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_neo4j():
    """Initialize Neo4j database with constraints and indexes"""
    logger.info("Setting up Neo4j database...")
    
    config = get_neo4j_config()
    
    with FundPortfolioManager(
        uri=config.url,
        user=config.username,
        password=config.password
    ) as manager:
        with manager.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT fund_id_unique IF NOT EXISTS FOR (f:Fund) REQUIRE f.fund_id IS UNIQUE",
                "CREATE CONSTRAINT instrument_id_unique IF NOT EXISTS FOR (i:Instrument) REQUIRE i.instrument_id IS UNIQUE",
                "CREATE CONSTRAINT snapshot_id_unique IF NOT EXISTS FOR (s:MonthlySnapshot) REQUIRE s.snapshot_id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"✅ Created constraint: {constraint[:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Constraint may already exist: {e}")
            
            # Create indexes
            indexes = [
                "CREATE INDEX fund_name_index IF NOT EXISTS FOR (f:Fund) ON (f.fund_name)",
                "CREATE INDEX instrument_name_index IF NOT EXISTS FOR (i:Instrument) ON (i.name)",
                "CREATE INDEX snapshot_date_index IF NOT EXISTS FOR (s:MonthlySnapshot) ON (s.year, s.month)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"✅ Created index: {index[:50]}...")
                except Exception as e:
                    logger.warning(f"⚠️ Index may already exist: {e}")
    
    logger.info("✅ Neo4j setup complete")


def setup_sqlite():
    """Initialize SQLite database"""
    logger.info("Setting up SQLite database...")
    
    config = get_database_config()
    db_path = config.sqlite_path
    
    # Ensure directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    if db_path.exists():
        logger.info(f"✅ SQLite database already exists at: {db_path}")
    else:
        logger.info(f"ℹ️ SQLite database will be created at: {db_path}")
        logger.info("   Please ensure you have loaded your fund performance data")
    
    logger.info("✅ SQLite setup complete")


def setup_directories():
    """Create necessary directories"""
    logger.info("Setting up directories...")
    
    settings = get_settings()
    
    directories = [
        Path(settings.raw_data_dir),
        Path(settings.processed_data_dir),
        Path("logs"),
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"✅ Created directory: {directory}")
    
    logger.info("✅ Directory setup complete")


def verify_configuration():
    """Verify that all required configuration is present"""
    logger.info("Verifying configuration...")
    
    try:
        settings = get_settings()
        
        required_fields = [
            ('azure_endpoint', settings.azure_endpoint),
            ('azure_key', settings.azure_key),
            ('groq_api_key', settings.groq_api_key),
            ('neo4j_url', settings.neo4j_url),
            ('neo4j_password', settings.neo4j_password),
            ('sqlite_db_path', settings.sqlite_db_path),
            ('isin_mapping_path', settings.isin_mapping_path),
        ]
        
        missing = []
        for field_name, field_value in required_fields:
            if not field_value or field_value == '...':
                missing.append(field_name)
        
        if missing:
            logger.error(f"❌ Missing required configuration fields: {', '.join(missing)}")
            logger.error("   Please update your .env file with valid credentials")
            return False
        
        logger.info("✅ Configuration verified")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration error: {e}")
        logger.error("   Please ensure .env file exists and is properly formatted")
        return False


def main():
    """Main setup function"""
    logger.info("="*60)
    logger.info("Fund Portfolio Intelligence System - Database Setup")
    logger.info("="*60)
    
    # Step 1: Verify configuration
    if not verify_configuration():
        logger.error("\n❌ Setup failed due to configuration errors")
        logger.info("Please check your .env file and try again")
        sys.exit(1)
    
    # Step 2: Setup directories
    setup_directories()
    
    # Step 3: Setup SQLite
    setup_sqlite()
    
    # Step 4: Setup Neo4j
    try:
        setup_neo4j()
    except Exception as e:
        logger.error(f"❌ Neo4j setup failed: {e}")
        logger.error("   Please verify your Neo4j credentials and connection")
        sys.exit(1)
    
    logger.info("\n" + "="*60)
    logger.info("✅ Setup Complete!")
    logger.info("="*60)
    logger.info("\nNext Steps:")
    logger.info("1. Place your ISIN master data CSV at: " + get_settings().isin_mapping_path)
    logger.info("2. Place your SQLite database at: " + str(get_database_config().sqlite_path))
    logger.info("3. Place PDF factsheets in: " + get_settings().raw_data_dir)
    logger.info("4. Run: python main.py")
    logger.info("\n")


if __name__ == "__main__":
    main()
