import logging
from pathlib import Path
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def collapse_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge duplicate column labels by taking the first non-null value per row.
    FastReport HTML often creates repeated headers because of colspans.
    """
    if df.columns.is_unique:
        return df

    collapsed = pd.DataFrame(index=df.index)
    for col in pd.unique(df.columns):
        same_named_cols = df.loc[:, df.columns == col]
        if same_named_cols.shape[1] == 1:
            collapsed[col] = same_named_cols.iloc[:, 0]
        else:
            collapsed[col] = same_named_cols.bfill(axis=1).iloc[:, 0]
    return collapsed

def extract_html_file(filepath: str) -> tuple[str, list[dict]] | None:
    try:
        path = Path(filepath)
        filename = path.name.upper()

        if "SESSION DATA" in filename:
            record_type = "session"
            headers_to_find = ["Cashier", "Terminal", "Session Type"]
        elif "CASH DATA" in filename:
            record_type = "cash"
            headers_to_find = ["Cashier", "Date", "Income/Expense"]
        elif "STOCK DATA" in filename:
            record_type = "stock"
            headers_to_find = ["Cashier", "Date", "Item Name"]
        elif "MEMBER DATA" in filename:
            record_type = "member"
            headers_to_find = ["ID", "Username", "Firstname"]
        else:
            logger.warning(f"Unknown report type for file: {filepath}")
            return None

        # pandas read_html handles all the merged cells/colspans natively if we let it
        try:
            dfs = pd.read_html(filepath, flavor='lxml', encoding='utf-8')
        except ValueError as e:
            logger.warning(f"No tables found or failed to parse HTML in {filepath}: {e}")
            return None
        
        valid_dfs = []
        for df in dfs:
            # Drop empty columns
            df = df.dropna(axis=1, how='all')
            
            # Find the row that contains our headers
            header_row_idx = None
            for idx, row in df.iterrows():
                row_str = " ".join([str(x) for x in row.values])
                if all(h in row_str for h in headers_to_find):
                    header_row_idx = idx
                    break
            
            if header_row_idx is not None:
                # Set headers and slice data
                df.columns = df.iloc[header_row_idx].astype(str).str.strip()
                df = df.iloc[header_row_idx + 1:].copy()
                
                # Merge duplicated columns created by colspans
                df = collapse_duplicate_columns(df)
                
                # Drop rows where everything is NaN
                df = df.dropna(axis=0, how='all')
                
                # Remove rows that might be sub-headers or totals if they don't match the structure
                if "Cashier" in df.columns:
                    df = df[~df['Cashier'].astype(str).str.contains('Total|nan', case=False, na=False)]
                if "ID" in df.columns:
                    df = df[~df['ID'].astype(str).str.contains('Total|nan', case=False, na=False)]
                    
                valid_dfs.append(df)
        
        if not valid_dfs:
            logger.warning(f"Could not find valid data table in {filepath}")
            return None
            
        target_df = pd.concat(valid_dfs, ignore_index=True)
            
        # Clean column names by stripping extra spaces, newlines, etc.
        def clean_col_name(c):
            # Sometimes FastReport puts `\xa0`
            c = str(c).replace('\xa0', ' ').strip()
            # If columns are duplicated (e.g., empty columns or repeated headers due to merged cells), pandas adds .1, .2
            # but we'll deal with column values via dictionary lookup.
            return c
        
        target_df.columns = [clean_col_name(c) for c in target_df.columns]
        
        # We replace NaNs with None for pure python dict
        target_df = target_df.replace({np.nan: None})
        
        records = target_df.to_dict('records')
        
        # Add source_file to each record
        for r in records:
            r['source_file'] = filepath
            
        return record_type, records

    except Exception as e:
        logger.error(f"Error extracting {filepath}: {e}", exc_info=True)
        return None
