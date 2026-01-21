"""
Holding Classifier Module
Classifies portfolio holdings into asset classes and sub-types using LLM
"""

import dspy
import json
from typing import List, Literal, Dict
from pydantic import BaseModel, Field
from src.utils.config import get_groq_config


# ============================================
# Asset Class Taxonomy
# ============================================

GROUP_SUBGROUP_MAP: Dict[str, List[str]] = {
    "EQUITY & EQUITY RELATED": [
        "Indian Equity",
        "Preferential Shares",
        "Foreign Equity",
        "REIT/INVIT",
        "Mutual Fund Units",
        "Index Options",
        "Stock Options",
        "Stock Futures",
        "Gold ETF",
        "Silver ETF",
    ],
    "CORPORATE DEBT": [
        "Corporate Bonds",
        "Non Convertible Debentures",
        "Convertible Debentures",
        "Pass Through Certificates",
        "Reduced Face Value Bonds - Non Amortisation",
        "Credit Exposure",
        "Zero Coupon Bond",
    ],
    "GOVERNMENT SECURITIES": [
        "Government Bonds",
        "State Government Bonds",
        "Treasury Bills",
    ],
    "SECURITISED DEBT": [
        "Securitised Debt",
        "Pass Through Certificate",
    ],
    "MONEY MARKET INSTRUMENTS": [
        "Certificate of Deposit",
        "Commercial Paper",
        "TREPS and Others",
    ],
    "OTHER": ['Commodity']
}

# Type definitions
GroupName = Literal[
    "EQUITY & EQUITY RELATED",
    "CORPORATE DEBT",
    "GOVERNMENT SECURITIES",
    "SECURITISED DEBT",
    "MONEY MARKET INSTRUMENTS",
    "OTHER"
]

SubGroupName = Literal[
    "Indian Equity",
    "Indian ETF",
    "Preferential Shares",
    "Foreign Equity",
    "Foreign ETF",
    "REIT/INVIT",
    "Mutual Fund Units",
    "Index Options",
    "Stock Options",
    "Stock Futures",
    "Gold ETF",
    "Silver ETF",
    "Corporate Bonds",
    "Commodity",
    "Non Convertible Debentures",
    "Pass Through Certificate",
    "Reduced Face Value Bonds - Non Amortisation",
    "Credit Exposure",
    "Government Bonds",
    "State Government Bonds",
    "Treasury Bills",
    "Zero Coupon Bond",
    "Securitised Debt",
    "Pass Through Certificates",
    "Certificate of Deposit",
    "Commercial Paper",
    "TREPS and Others",
]


# ============================================
# Pydantic Models
# ============================================

class Holding(BaseModel):
    """Individual holding item"""
    name: str = Field(..., min_length=1)
    percentage_to_net_assets: float = Field(...)


class Group(BaseModel):
    """Asset class group"""
    group_name: GroupName
    asset_class: SubGroupName
    sub_type: List[Holding]


# ============================================
# DSPy Signature
# ============================================

class CleanGroupedTable(dspy.Signature):
    """
    Clean OCR-extracted fund portfolio tables.

    Rules:
    - Identify asset_class AND sub_type
    - asset_class must be one of:
        EQUITY & EQUITY RELATED
        CORPORATE DEBT
        GOVERNMENT SECURITIES
        SECURITISED DEBT
        MONEY MARKET INSTRUMENTS
        OTHER
    - sub_type must be logically valid for the asset_class
    - For EQUITY & EQUITY RELATED group:
      Sector names such as Banking, IT, Pharma, FMCG, Energy, Metals, etc.
      MUST NOT be used as sub_type.
      Use sub_type = "Indian Equity" or "Foreign Equity" unless
      the instrument type is explicitly different (REIT, INVIT, etc.)
    - Ignore totals, headers, ratings, summaries
    """

    table_input: str = dspy.InputField(
        desc="Raw OCR text or markdown table"
    )

    json_output: str = dspy.OutputField(
        desc=(
            "STRICT JSON ARRAY ONLY.\n"
            "Each element must be:\n"
            "{\n"
            "  \"group_name\": string,\n"
            "  \"sub_group\": string,\n"
            "  \"items\": [\n"
            "    { \"name\": string, \"percentage_to_net_assets\": number }\n"
            "  ]\n"
            "}\n"
            "Use only valid group/sub_group combinations."
        )
    )


# ============================================
# Table Cleaner Module
# ============================================

class TableCleanerCoT(dspy.Module):
    """Chain-of-Thought table cleaner using DSPy"""
    
    def __init__(self, config=None):
        super().__init__()
        
        # Use config if provided, otherwise get from settings
        if config is None:
            config = get_groq_config()
        
        # Configure DSPy with Groq
        lm = dspy.LM(
            model=f"groq/{config.model}",
            api_key=config.api_key,
            temperature=config.temperature
        )
        dspy.configure(lm=lm)
        
        # Initialize chain of thought
        self.prog = dspy.ChainOfThought(CleanGroupedTable)

    def forward(self, table_input: str):
        """Process table input and return cleaned output"""
        return self.prog(table_input=table_input)
    
    def clean_and_parse(self, table_input: str) -> List[Dict]:
        """
        Clean table and parse to structured format
        
        Args:
            table_input: Raw table text
            
        Returns:
            List of dictionaries with cleaned data
        """
        result = self.forward(table_input)
        
        try:
            # Extract JSON from markdown if present
            json_str = result.json_output.strip()
            if json_str.startswith('```json'):
                json_str = json_str.split('```json')[1].split('```')[0]
            elif json_str.startswith('```'):
                json_str = json_str.split('```')[1].split('```')[0]
            
            # Parse JSON
            parsed_data = json.loads(json_str.strip())
            return parsed_data
            
        except (json.JSONDecodeError, AttributeError, IndexError) as e:
            print(f"⚠️ Failed to parse JSON output: {e}")
            return []


# ============================================
# Validation Utilities
# ============================================

def validate_asset_classification(group_name: str, sub_group: str) -> bool:
    """
    Validate that sub_group is valid for the given group_name
    
    Args:
        group_name: Main asset class
        sub_group: Sub-category
        
    Returns:
        True if valid combination
    """
    valid_subgroups = GROUP_SUBGROUP_MAP.get(group_name, [])
    return sub_group in valid_subgroups


def get_valid_subgroups(group_name: str) -> List[str]:
    """
    Get list of valid subgroups for a given asset class
    
    Args:
        group_name: Main asset class
        
    Returns:
        List of valid sub-categories
    """
    return GROUP_SUBGROUP_MAP.get(group_name, [])


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    # Test the classifier
    sample_table = """
    | Security | % to Net Assets |
    |----------|----------------|
    | HDFC Bank Ltd | 9.18 |
    | ICICI Bank Ltd | 7.00 |
    | Treasury Bills | 1.30 |
    | TREPS | 5.11 |
    """
    
    classifier = TableCleanerCoT()
    result = classifier.clean_and_parse(sample_table)
    
    print("Cleaned Output:")
    print(json.dumps(result, indent=2))
