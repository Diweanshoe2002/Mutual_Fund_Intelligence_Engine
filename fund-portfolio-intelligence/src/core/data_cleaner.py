"""
Data Cleaner Module
LangGraph-based agent for cleaning and normalizing OCR table data
"""

import os
import json
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Optional, TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from src.core.holding_classifier import TableCleanerCoT
from src.utils.config import get_groq_config, get_data_config


# ============================================
# State Definition
# ============================================

class CleaningState(TypedDict):
    """State for the data cleaning graph"""
    raw_data: str
    dataframe_input: Optional[pd.DataFrame]
    cleaned_json: Optional[List[Dict]]
    Data: Optional[List[Dict]]
    Final_output: Optional[List[Dict]]
    validation_errors: List[str]
    messages: Annotated[List, add_messages]
    fund_name: Optional[str]


# ============================================
# ISIN Mapper
# ============================================

class ISINMapper:
    """Maps stock names to ISIN codes using master data"""
    
    def __init__(self, mapping_path: Optional[str] = None):
        """
        Initialize ISIN mapper
        
        Args:
            mapping_path: Path to ISIN mapping CSV. If None, loads from config
        """
        self.isin_mapping = {}
        self.market_cap_mapping = {}
        
        if mapping_path is None:
            config = get_data_config()
            mapping_path = str(config.isin_mapping_path)
        
        self._load_mappings(mapping_path)
    
    def _load_mappings(self, path: str):
        """Load ISIN and market cap mappings from CSV"""
        if not os.path.exists(path):
            print(f"⚠️ ISIN mapping file not found: {path}")
            return
        
        try:
            df = pd.read_csv(path, encoding='latin1')
            df.columns = df.columns.str.strip()
            
            for _, row in df.iterrows():
                company_name = str(row.get('NAME OF COMPANY', '')).strip().lower()
                # Normalize company name
                company_name = (
                    company_name
                    .replace('&amp;', '&')
                    .replace('Ltd.', 'limited')
                    .replace('Ltd', 'limited')
                )
                
                isin = str(row.get('ISIN NUMBER', '')).strip()
                market_cap = str(row.get('MARKET CAP', '')).strip()
                
                if company_name and isin:
                    self.isin_mapping[company_name] = isin
                if company_name and market_cap:
                    self.market_cap_mapping[company_name] = market_cap
            
            print(f"✅ Loaded {len(self.isin_mapping)} ISIN mappings")
            
        except Exception as e:
            print(f"❌ Error loading ISIN mapping: {e}")
    
    def map_stock_to_isin(self, stock_name: str) -> Optional[str]:
        """
        Map a stock name to its ISIN
        
        Args:
            stock_name: Company name
            
        Returns:
            ISIN code or None if not found
        """
        if not stock_name or not self.isin_mapping:
            return None
        
        # Normalize search key
        search_key = stock_name.strip().lower()
        search_key = (
            search_key
            .replace('&amp;', '&')
            .replace('ltd.', 'limited')
            .replace('ltd', 'limited')
        )
        
        isin = self.isin_mapping.get(search_key)
        if not isin:
            print(f"⚠️ ISIN not found for '{stock_name}'")
        
        return isin
    
    def get_market_cap(self, stock_name: str) -> Optional[str]:
        """Get market cap for a stock"""
        if not stock_name or not self.market_cap_mapping:
            return None
        
        search_key = stock_name.strip().lower()
        search_key = (
            search_key
            .replace('&amp;', '&')
            .replace('ltd.', 'limited')
            .replace('ltd', 'limited')
        )
        
        return self.market_cap_mapping.get(search_key)


# ============================================
# Data Cleaning Agent
# ============================================

class DataCleaningAgent:
    """LangGraph agent for OCR table normalization"""
    
    def __init__(
        self, 
        llm_model: Optional[str] = None,
        temperature: float = 0.1,
        isin_mapping_path: Optional[str] = None
    ):
        """
        Initialize data cleaning agent
        
        Args:
            llm_model: Optional LLM model name
            temperature: LLM temperature
            isin_mapping_path: Path to ISIN mapping file
        """
        # Get configuration
        config = get_groq_config()
        if llm_model is None:
            llm_model = config.model
        
        # Initialize LLM
        self.llm = ChatGroq(
            model=llm_model,
            temperature=temperature,
            api_key=config.api_key
        )
        
        # Initialize ISIN mapper
        self.isin_mapper = ISINMapper(isin_mapping_path)
        
        # Build LangGraph
        self.graph = self._build_graph()
        self.app = self.graph.compile()
        
        # Accumulated results for batch processing
        self.accumulated_results = []
        
        self.system_prompt = """You are a table normalizer for OCR data.
        Reconstruct the table with these columns:
        - Stock Name
        - pct_total_aum

        Rules:
        • Keep full company names intact.
        • Use null for missing.
        • Consider Gross Exposure,% to Net Assets as pct_total_aum if present.
        • Output JSON array only, no explanations."""
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(CleaningState)
        
        # Add nodes
        workflow.add_node("extract_text", self.extract_text_node)
        workflow.add_node("normalize", self.normalize_node)
        workflow.add_node("to_dataframe", self.to_dataframe_node)
        
        # Set entry point
        workflow.set_entry_point("extract_text")
        
        # Add edges
        workflow.add_edge("extract_text", "normalize")
        workflow.add_edge("normalize", "to_dataframe")
        workflow.add_edge("to_dataframe", END)
        
        return workflow
    
    def extract_text_node(self, state: CleaningState) -> CleaningState:
        """Extract text from DataFrame"""
        df = state.get("dataframe_input")
        if df is not None:
            state["raw_data"] = df.to_markdown(index=False)
            print(f"📝 Extracted text:\n{state['raw_data'][:200]}...")
        return state
    
    def normalize_node(self, state: CleaningState) -> CleaningState:
        """Normalize table using LLM"""
        raw_input = state['raw_data']
        classifier = TableCleanerCoT()
        
        try:
            result = classifier.clean_and_parse(raw_input)
            state["cleaned_json"] = result
            print(f"✅ Normalized: {len(result)} groups")
        except Exception as e:
            print(f"❌ Normalization error: {e}")
            state["cleaned_json"] = []
        
        return state
    
    def to_dataframe_node(self, state: CleaningState) -> CleaningState:
        """Transform normalized data to final format"""
        refined_data = state.get("cleaned_json", [])
        fund_name = state.get("fund_name", "Unknown Fund")
        final_output = []
        
        if refined_data:
            for group in refined_data:
                # Extract parent info
                asset_class = group.get("group_name")
                sub_type = group.get("sub_group")
                
                # Process individual items and flatten
                for item in group.get("items", []):
                    stock_name = item.get("name")
                    
                    # Only look up ISIN for equity instruments
                    isin = None
                    if asset_class == "EQUITY & EQUITY RELATED":
                        if sub_type in ["Indian Equity", "Foreign Equity"]:
                            isin = self.isin_mapper.map_stock_to_isin(stock_name)
                    
                    new_item = {
                        "fund_name": fund_name,
                        "name": stock_name,
                        "stock_id": isin,
                        "weights": item.get("percentage_to_net_assets"),
                        "market_cap": self.isin_mapper.get_market_cap(stock_name),
                        "asset_class": asset_class,
                        "sub_type": sub_type
                    }
                    
                    final_output.append(new_item)
            
            print(f"✅ Transformed {len(final_output)} items for {fund_name}")
            
            # Accumulate for batch saving
            self.accumulated_results.extend(final_output)
        
        state["Final_output"] = final_output
        return state
    
    def clean_dataframe(
        self, 
        df: pd.DataFrame, 
        fund_name: Optional[str] = None
    ) -> List[Dict]:
        """
        Clean a single DataFrame
        
        Args:
            df: Input DataFrame
            fund_name: Optional fund name
            
        Returns:
            List of cleaned records
        """
        init_state = {
            "raw_data": "",
            "dataframe_input": df,
            "cleaned_json": None,
            "Data": None,
            "Final_output": None,
            "validation_errors": [],
            "messages": [],
            "fund_name": fund_name
        }
        
        final = self.app.invoke(init_state)
        return final.get("Final_output", [])
    
    def save_results(self, output_file: str):
        """
        Save accumulated results to JSON file
        
        Args:
            output_file: Path to output file
        """
        # Get output directory from config
        config = get_data_config()
        output_path = config.processed_data_dir / output_file
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.accumulated_results, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(self.accumulated_results)} items to {output_path}")
        
        # Reset accumulator
        self.accumulated_results = []


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    # Test the cleaner
    sample_df = pd.DataFrame({
        'Security': ['HDFC Bank Ltd', 'ICICI Bank Ltd', 'Treasury Bills', 'TREPS'],
        '% to NAV': [9.18, 7.0, 1.3, 5.11]
    })
    
    agent = DataCleaningAgent()
    result = agent.clean_dataframe(sample_df, fund_name="Test Fund")
    
    print("\nCleaned Output:")
    print(json.dumps(result, indent=2))
