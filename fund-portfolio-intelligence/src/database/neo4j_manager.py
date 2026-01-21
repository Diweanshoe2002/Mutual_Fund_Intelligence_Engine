"""
Neo4j Database Manager
Manages fund portfolio data in Neo4j graph database
"""

import logging
from typing import Dict, List, Optional
from neo4j import GraphDatabase
from datetime import date

from src.utils.config import get_neo4j_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FundPortfolioManager:
    """Manages fund portfolio data in Neo4j"""
    
    def __init__(self, uri: Optional[str] = None, user: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        Initialize Neo4j connection
        
        Args:
            uri: Neo4j connection URI (optional, loads from config if None)
            user: Neo4j username (optional)
            password: Neo4j password (optional)
        """
        # Load from config if not provided
        if uri is None or user is None or password is None:
            config = get_neo4j_config()
            uri = uri or config.url
            user = user or config.username
            password = password or config.password
        
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info("Connected to Neo4j")
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
        logger.info("Closed Neo4j connection")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
    
    # =========================================================================
    # STEP 1: CREATE INSTRUMENT NODES
    # =========================================================================
    
    def create_instruments(self, instruments_data: List[Dict]) -> int:
        """
        Create instrument nodes from input data.
        
        Args:
            instruments_data: List of dicts with keys:
                - name or Stock_Name
                - instrument_id or stock_id (ISIN or other ID)
                - asset_class (optional)
                - sub_type (optional)
        
        Returns:
            Number of instruments created or merged
        """
        query = """
        UNWIND $instruments AS row
        MERGE (i:Instrument {instrument_id: row.instrument_id})
        ON CREATE SET
            i.name        = row.name,
            i.asset_class = row.asset_class,
            i.sub_type    = row.sub_type
        RETURN count(i) AS instruments_created
        """
        
        # Transform data to match query parameters
        transformed_data = []
        for item in instruments_data:
            name = item.get("name") or item.get("Stock_Name")
            instrument_id = item.get("instrument_id") or item.get("stock_id")
            asset_class = item.get("asset_class")
            sub_type = item.get("sub_type")
            
            if instrument_id:  # Only add if we have an ID
                transformed_data.append({
                    "instrument_id": instrument_id,
                    "name": name,
                    "asset_class": asset_class,
                    "sub_type": sub_type,
                })
        
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(query, instruments=transformed_data).single()
            )
            instruments_created = result["instruments_created"]
            logger.info(f"Created/merged {instruments_created} instruments")
            return instruments_created
    
    # =========================================================================
    # STEP 2: CREATE FUND NODE
    # =========================================================================
    
    def create_fund(self, fund_id: int, fund_name: str, amc: str, 
                    category: Optional[str] = None) -> Dict:
        """
        Create a fund node
        
        Args:
            fund_id: Unique fund identifier
            fund_name: Name of the fund
            amc: Asset Management Company
            category: Fund category (optional)
        
        Returns:
            Created fund details
        """
        query = """
        MERGE (f:Fund {fund_id: $fund_id})
        ON CREATE SET
            f.fund_name = $fund_name,
            f.amc = $amc,
            f.category = $category
        RETURN f.fund_id AS fund_id, f.fund_name AS fund_name
        """
        
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    query,
                    fund_id=fund_id,
                    fund_name=fund_name,
                    amc=amc,
                    category=category
                ).single()
            )
            logger.info(f"Created fund {result['fund_name']}")
            return dict(result)
    
    # =========================================================================
    # STEP 3: CREATE MONTHLY SNAPSHOT
    # =========================================================================
    
    def create_snapshot(self, snapshot_id: str, fund_id: int, year: int, 
                       month: int, total_aum: float, num_holdings: int) -> Dict:
        """
        Create a monthly snapshot for a fund
        
        Args:
            snapshot_id: Unique snapshot identifier
            fund_id: Fund identifier
            year: Year (e.g., 2025)
            month: Month (1-12)
            total_aum: Total AUM in crores
            num_holdings: Number of holdings in this snapshot
        
        Returns:
            Created snapshot details
        """
        query = """
        CREATE (snap:MonthlySnapshot {
            snapshot_id: $snapshot_id,
            fund_id: $fund_id,
            year: $year,
            month: $month,
            total_aum: $total_aum,
            num_holdings: $num_holdings
        })
        RETURN snap.snapshot_id AS snapshot_id
        """
        
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    query,
                    snapshot_id=snapshot_id,
                    fund_id=fund_id,
                    year=year,
                    month=month,
                    total_aum=total_aum,
                    num_holdings=num_holdings,
                ).single()
            )
            logger.info(f"Created snapshot {result['snapshot_id']}")
            return dict(result)
    
    # =========================================================================
    # STEP 4: LINK SNAPSHOT TO FUND
    # =========================================================================
    
    def link_snapshot_to_fund(self, fund_id: int, snapshot_id: str) -> bool:
        """
        Create [:LATEST_SNAPSHOT] relationship between Fund and Snapshot
        
        Args:
            fund_id: Fund identifier
            snapshot_id: Snapshot identifier
        
        Returns:
            True if successful
        """
        query = """
        MATCH (f:Fund {fund_id: $fund_id})
        MATCH (snap:MonthlySnapshot {snapshot_id: $snapshot_id})
        CREATE (f)-[:LATEST_SNAPSHOT]->(snap)
        RETURN f.fund_id AS fund_id, snap.snapshot_id AS snapshot_id
        """
        
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    query,
                    fund_id=fund_id,
                    snapshot_id=snapshot_id,
                ).single()
            )
            logger.info(f"Linked fund {result['fund_id']} to snapshot {result['snapshot_id']}")
            return True
    
    # =========================================================================
    # STEP 5: ADD HOLDINGS
    # =========================================================================
    
    def add_holdings(self, holdings_data: List[Dict]) -> int:
        """
        Add holdings to a snapshot
        
        Args:
            holdings_data: List of dicts with keys:
                - snapshot_id
                - instrument_id or stock_id
                - weights or weight
        
        Returns:
            Number of holdings created
        """
        query = """
        UNWIND $holdings AS holding
        MATCH (snap:MonthlySnapshot {snapshot_id: holding.snapshot_id})
        MATCH (i:Instrument {instrument_id: holding.instrument_id})
        CREATE (snap)-[:HOLDS {
            weight: holding.weight
        }]->(i)
        RETURN count(*) AS holdings_created
        """
        
        transformed_data = []
        for holding in holdings_data:
            instrument_id = holding.get("instrument_id") or holding.get("stock_id")
            weight = holding.get("weights") or holding.get("weight")
            
            if instrument_id and holding.get("snapshot_id"):
                transformed_data.append({
                    "snapshot_id": holding["snapshot_id"],
                    "instrument_id": instrument_id,
                    "weight": weight,
                })
        
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(query, holdings=transformed_data).single()
            )
            holdings_created = result["holdings_created"]
            logger.info(f"Created {holdings_created} holdings")
            return holdings_created
    
    # =========================================================================
    # STEP 6: CREATE CURRENT HOLDINGS
    # =========================================================================
    
    def create_current_holdings(self, fund_id: int, snapshot_id: str) -> int:
        """
        Create [:CURRENT_HOLDINGS] relationships from fund to instruments
        based on the latest snapshot
        
        Args:
            fund_id: Fund identifier
            snapshot_id: Snapshot identifier to use as source
        
        Returns:
            Number of current holdings created
        """
        query = """
        MATCH (f:Fund {fund_id: $fund_id})-[:LATEST_SNAPSHOT]->(snap:MonthlySnapshot {snapshot_id: $snapshot_id})
        MATCH (snap)-[h:HOLDS]->(i:Instrument)
        CREATE (f)-[:CURRENT_HOLDINGS {
            weight: h.weight
        }]->(i)
        RETURN count(*) AS current_holdings_created
        """
        
        with self.driver.session() as session:
            result = session.execute_write(
                lambda tx: tx.run(
                    query,
                    fund_id=fund_id,
                    snapshot_id=snapshot_id,
                ).single()
            )
            current_created = result["current_holdings_created"]
            logger.info(f"Created {current_created} current holdings")
            return current_created
    
    # =========================================================================
    # HELPER: LOAD COMPLETE PORTFOLIO
    # =========================================================================
    
    def load_portfolio(self, fund_id: int, fund_name: str, amc: str,
                       snapshot_id: str, year: int, month: int,
                       total_aum: float, holdings_data: List[Dict]) -> Dict:
        """
        Complete portfolio loading workflow
        
        Args:
            fund_id: Fund identifier
            fund_name: Fund name
            amc: AMC name
            snapshot_id: Snapshot identifier
            year: Year
            month: Month
            total_aum: Total AUM
            holdings_data: List of holdings with instrument_id and weights
        
        Returns:
            Summary of operations performed
        """
        # Step 1: Create instruments
        instruments_created = self.create_instruments(holdings_data)
        
        # Step 2: Create fund
        fund = self.create_fund(fund_id, fund_name, amc)
        
        # Step 3: Create snapshot
        snapshot = self.create_snapshot(
            snapshot_id, fund_id, year, month, total_aum, len(holdings_data)
        )
        
        # Step 4: Link snapshot to fund
        self.link_snapshot_to_fund(fund_id, snapshot_id)
        
        # Step 5: Add holdings (add snapshot_id to each)
        holdings_with_snapshot = [
            {**h, "snapshot_id": snapshot_id} for h in holdings_data
        ]
        holdings_created = self.add_holdings(holdings_with_snapshot)
        
        # Step 6: Create current holdings
        current_created = self.create_current_holdings(fund_id, snapshot_id)
        
        return {
            "instruments_created": instruments_created,
            "fund_id": fund["fund_id"],
            "snapshot_id": snapshot["snapshot_id"],
            "holdings_created": holdings_created,
            "current_holdings_created": current_created
        }


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    # Test the manager
    with FundPortfolioManager() as manager:
        # Sample holdings data
        holdings = [
            {
                "name": "HDFC Bank Limited",
                "instrument_id": "INE040A01034",
                "weights": 9.18,
                "asset_class": "EQUITY & EQUITY RELATED",
                "sub_type": "Indian Equity"
            },
            {
                "name": "ICICI Bank Limited",
                "instrument_id": "INE090A01021",
                "weights": 7.0,
                "asset_class": "EQUITY & EQUITY RELATED",
                "sub_type": "Indian Equity"
            }
        ]
        
        result = manager.load_portfolio(
            fund_id=9109,
            fund_name="Test Fund",
            amc="Test AMC",
            snapshot_id="202501",
            year=2025,
            month=1,
            total_aum=1000.0,
            holdings_data=holdings
        )
        
        print(f"\n✅ Portfolio loaded: {result}")
