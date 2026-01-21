"""
SQL Tools Module
Custom tools for SQL database operations including fund screening and benchmarks
"""

from typing import Literal
from pydantic import BaseModel, Field, model_validator
from langchain.tools import tool
from langchain_community.agent_toolkits import SQLDatabaseToolkit
import yfinance as yf


# ============================================
# Tool Input Models
# ============================================

class BenchmarkInput(BaseModel):
    """Input parameters for fetching benchmark data"""
    benchmark: str = Field(
        ...,
        description="The ticker symbol of the benchmark (e.g., ^NSEI, ^CRSLDX)"
    )
    period: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y"] = Field(
        "1y",
        description="The time frame for fetching data."
    )


class ScreenerInput(BaseModel):
    """Input parameters for the mutual fund screener"""
    weight_returns_3m: float = Field(
        ...,
        description="Weight given to Return of a fund for the last 3 months."
    )
    weight_alpha_1y: float = Field(
        ...,
        description="Weight given to Alpha of a fund for the last 1 year."
    )
    weight_beta_1y: float = Field(
        ...,
        description="Weight given to Beta of a fund for the last 1 year."
    )
    category: str = Field(
        ...,
        description="Category of funds to screen, e.g., 'Large cap funds', 'Mid cap funds', 'Flexi cap funds'."
    )
    
    @model_validator(mode="after")
    def check_weights_sum(self):
        """Validate that weights sum to approximately 1.0"""
        total = self.weight_returns_3m + self.weight_alpha_1y + self.weight_beta_1y
        if not (0.99 <= total <= 1.01):  # Allow tiny float tolerance
            raise ValueError(f"Sum of weights must be 100%. Got {total:.2f}")
        return self


# ============================================
# Custom Tools
# ============================================

@tool(args_schema=BenchmarkInput)
def get_benchmark_data(benchmark: str, period: str) -> str:
    """
    Fetches the point-to-point return for a given stock market benchmark over a specified period.
    
    The `benchmark` argument is the ticker symbol (e.g., ^NSEI for Nifty 50).
    
    Following are valid benchmark tickers:
    - ^NSEI - Nifty 50
    - ^CNX100 - Nifty 100
    - NIFTYMIDCAP150.NS - Nifty Midcap 150
    - ^CRSLDX - Nifty 500
    
    The `period` argument is the time frame, one of: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y".
    
    Returns:
        Point-to-point return percentage as a string
    """
    try:
        benchmark_index = yf.Ticker(benchmark)
        benchmark_data = benchmark_index.history(period=period)['Close']
        
        if benchmark_data.empty:
            return f"Could not fetch data for ticker: {benchmark}"
        
        initial_price = benchmark_data.iloc[0]
        final_price = benchmark_data.iloc[-1]
        point_to_point_return = ((final_price - initial_price) / initial_price) * 100
        
        return f"{point_to_point_return:.2f}%"
    
    except Exception as e:
        return f"Error fetching benchmark data: {str(e)}"


@tool(args_schema=ScreenerInput)
def mutual_fund_screener(
    weight_returns_3m: float,
    weight_alpha_1y: float,
    weight_beta_1y: float,
    category: str
) -> str:
    """
    Screens mutual funds based on weighted performance metrics and ranks them.
    
    This tool requires human approval before execution due to its analytical nature.
    
    Args:
        weight_returns_3m: Weight for 3-month returns (0-1)
        weight_alpha_1y: Weight for 1-year alpha (0-1)
        weight_beta_1y: Weight for 1-year beta (0-1)
        category: Fund category to screen
    
    Returns:
        Ranked list of funds with aggregate scores
    """
    # Map category to table name
    category_table_map = {
        "Large cap funds": "LARGE_CAP_FUNDS",
        "Mid cap funds": "MID_CAP_FUNDS",
        "Flexi cap funds": "FLEXI_CAP_FUNDS",
        "Small cap funds": "SMALL_CAP_FUNDS"
    }
    
    table_name = category_table_map.get(category)
    
    if not table_name:
        return f"Invalid category: {category}. Valid options: {list(category_table_map.keys())}"
    
    # Note: This returns the query string
    # Actual execution happens through the SQL agent
    query = f"""
    SELECT Fund_Name, 
           ( (Returns_3m * {weight_returns_3m}) + 
             (Alpha_1y * {weight_alpha_1y}) +
             (Beta_1y * {weight_beta_1y}) ) AS aggregate_score
    FROM {table_name}
    ORDER BY aggregate_score DESC
    LIMIT 10;
    """
    
    return query


# ============================================
# Tool Collection
# ============================================

def get_all_tools(db, llm):
    """
    Get all tools including SQL toolkit and custom tools
    
    Args:
        db: SQLDatabase instance
        llm: Language model instance
    
    Returns:
        List of all available tools
    """
    # SQL Database Toolkit
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    sql_tools = toolkit.get_tools()
    
    # Custom tools
    custom_tools = [
        mutual_fund_screener,
        get_benchmark_data
    ]
    
    # Combine all tools
    all_tools = sql_tools + custom_tools
    
    return all_tools


# ============================================
# Tool Descriptions
# ============================================

TOOL_DESCRIPTIONS = {
    "mutual_fund_screener": """
    Screens and ranks mutual funds based on weighted performance metrics.
    Requires human approval. Supports Large cap, Mid cap, Flexi cap, and Small cap funds.
    """,
    
    "get_benchmark_data": """
    Fetches point-to-point returns for Indian market benchmarks.
    Supports Nifty 50, Nifty 100, Nifty Midcap 150, and Nifty 500.
    """,
}


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    # Test tools
    print("Testing get_benchmark_data:")
    result = get_benchmark_data.invoke({"benchmark": "^NSEI", "period": "1y"})
    print(f"Nifty 50 (1Y): {result}")
    
    print("\nTesting mutual_fund_screener:")
    result = mutual_fund_screener.invoke({
        "weight_returns_3m": 0.5,
        "weight_alpha_1y": 0.3,
        "weight_beta_1y": 0.2,
        "category": "Large cap funds"
    })
    print(f"Query: {result}")
