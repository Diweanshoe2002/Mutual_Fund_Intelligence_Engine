"""
PDF Extractor Module
Extracts tables from PDF factsheets using Azure Document Intelligence
"""

import base64
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Optional
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient

from src.utils.config import get_azure_config


class PDFTableExtractor:
    """Extract tables from PDF documents using Azure Document Intelligence"""
    
    def __init__(self, config=None):
        """
        Initialize PDF extractor
        
        Args:
            config: Optional AzureConfig object. If None, loads from settings
        """
        if config is None:
            config = get_azure_config()
        
        self.client = DocumentIntelligenceClient(
            endpoint=config.endpoint,
            credential=AzureKeyCredential(config.key)
        )
    
    def _load_file_as_base64(self, file_path: str) -> str:
        """
        Convert PDF to base64 string for Azure request
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Base64 encoded string
        """
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    
    def extract_tables(self, file_path: str) -> Dict[str, List[pd.DataFrame]]:
        """
        Extract tables from PDF and group them by detected fund name
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary mapping fund names to list of DataFrames
        """
        print(f"📄 Extracting tables from: {file_path}")
        
        # Start analysis
        poller = self.client.begin_analyze_document(
            "prebuilt-layout",
            {"base64Source": self._load_file_as_base64(file_path)}
        )
        result = poller.result()
        
        print(f"✅ Found {len(result.pages)} pages and {len(result.tables)} tables.\n")
        
        # Group tables by page
        tables_by_page = defaultdict(list)
        for table_idx, table in enumerate(result.tables):
            page_number = (
                table.bounding_regions[0].page_number 
                if table.bounding_regions else None
            )
            rows, cols = table.row_count, table.column_count
            
            # Create empty DataFrame
            df = pd.DataFrame([[""] * cols for _ in range(rows)])
            
            # Fill DataFrame with cell content
            for cell in table.cells:
                df.iat[cell.row_index, cell.column_index] = str(cell.content).strip()
            
            tables_by_page[page_number].append((table_idx, df))
        
        # Detect fund names and merge tables
        merged_tables_by_fund = defaultdict(list)
        
        for page, tables in sorted(tables_by_page.items()):
            # Detect fund name from page text
            fund_name = self._detect_fund_name(result.pages, page)
            
            # Merge consecutive tables with same headers
            i = 0
            while i < len(tables):
                table_idx, df = tables[i]
                merged_df = df.copy()
                
                # Look for continuation tables
                j = i + 1
                while j < len(tables):
                    next_idx, next_df = tables[j]
                    if tuple(df.iloc[0].values) == tuple(next_df.iloc[0].values):
                        # Same headers - merge
                        merged_df = pd.concat(
                            [merged_df, next_df.iloc[1:]], 
                            ignore_index=True
                        )
                        j += 1
                    else:
                        break
                
                if fund_name:
                    merged_tables_by_fund[fund_name].append(merged_df)
                
                i = j if j > i + 1 else i + 1
        
        return merged_tables_by_fund
    
    def _detect_fund_name(self, pages: List, page_number: int) -> Optional[str]:
        """
        Detect fund name from page text
        
        Args:
            pages: List of page objects from Azure result
            page_number: Page number to analyze
            
        Returns:
            Detected fund name or None
        """
        fund_name = None
        
        for page in pages:
            if page.page_number == page_number:
                for idx, line in enumerate(page.lines):
                    if "fund" in line.content.lower():
                        # Found line with "fund" keyword
                        current_line = line.content.strip()
                        
                        # Check if there's a line above
                        if idx > 0:
                            previous_line = page.lines[idx - 1].content.strip()
                            # Combine previous line and current line
                            fund_name = f"{previous_line} {current_line}"
                        else:
                            # No line above, just use current line
                            fund_name = current_line
                        
                        # Clean up extra spaces
                        fund_name = " ".join(fund_name.split())
                        break
                
                # Fallback: if no "fund" keyword found, use first line
                if not fund_name and page.lines:
                    fund_name = page.lines[0].content.strip()
                
                print(f"📄 Page {page_number}: Detected fund name: '{fund_name}'")
                break
        
        return fund_name


class FundPortfolioProcessor:
    """
    High-level processor for fund portfolio extraction pipeline
    Combines PDF extraction with data cleaning
    """
    
    def __init__(self):
        """Initialize processor with extractor and cleaner"""
        from src.core.data_cleaner import DataCleaningAgent
        
        self.extractor = PDFTableExtractor()
        self.cleaner = DataCleaningAgent()
    
    def process_pdf(
        self, 
        file_path: str, 
        output_file: Optional[str] = None
    ) -> Dict[str, List[pd.DataFrame]]:
        """
        Full pipeline: extract tables → clean via LLM
        
        Args:
            file_path: Path to PDF file
            output_file: Optional output JSON file path
            
        Returns:
            Dictionary mapping fund names to cleaned DataFrames
        """
        # Step 1: Extract tables
        all_fund_tables = self.extractor.extract_tables(file_path)
        
        # Step 2: Clean tables
        cleaned_results = {}
        
        for fund, tables in all_fund_tables.items():
            cleaned_results[fund] = []
            for df in tables:
                print(f"\n🧩 Cleaning table for fund: {fund}")
                cleaned_df = self.cleaner.clean_dataframe(df, fund_name=fund)
                cleaned_results[fund].append(cleaned_df)
        
        # Step 3: Save if output file specified
        if output_file:
            self.cleaner.save_results(output_file)
        
        return cleaned_results


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_file_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    processor = FundPortfolioProcessor()
    results = processor.process_pdf(pdf_path, output_file="extracted_holdings.json")
    
    print("\n✅ Final Cleaned Output:")
    for fund, dfs in results.items():
        print(f"\nFund: {fund}")
        for i, df in enumerate(dfs):
            print(f"Table {i}: {len(df)} rows")
