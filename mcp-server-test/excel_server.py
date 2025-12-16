"""
MCP Server for Excel Data Processing

This server provides tools for reading, processing, analyzing, and visualizing Excel data.

Available Tools:
1. read_excel: Read Excel file from URL and convert to dict
2. filter_rows: Filter rows based on conditions
3. aggregate: Aggregate data (sum, average, groupBy)
4. apply_formula: Apply formula calculations on columns
5. plot_chart: Generate various chart types (line, bar, column, pie, scatter, area, histogram, box)
6. export_excel: Export processed data to Excel file
"""

from fastmcp import FastMCP
from typing import List, Dict, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

# Configure matplotlib to support Chinese characters
try:
    # Try to use common Chinese fonts
    import platform
    system = platform.system()
    if system == 'Darwin':  # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'PingFang SC', 'STHeiti']
    elif system == 'Windows':
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun']
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'Droid Sans Fallback']
    plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display
except Exception:
    pass  # If font configuration fails, use default fonts

# Try to import seaborn for better-looking charts
try:
    import seaborn as sns
    sns.set_style("whitegrid")
    sns.set_palette("husl")
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False
import requests
import os
import tempfile
from datetime import datetime
from pathlib import Path
import json
import threading
import http.server
import socketserver
import logging
import sys
import traceback

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Excel Data Processor")

# Configuration for file storage and serving
OUTPUT_DIR = Path(tempfile.gettempdir()) / "excel_mcp_outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# Simple HTTP server for serving files
FILE_SERVER_PORT = 8899
FILE_SERVER_HOST = "0.0.0.0"


def convert_numpy_types(obj):
    """
    Convert numpy types to Python native types for JSON serialization.
    
    Args:
        obj: Object that may contain numpy types
        
    Returns:
        Object with numpy types converted to Python native types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


class FileServerHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from OUTPUT_DIR"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(OUTPUT_DIR), **kwargs)
    
    def log_message(self, format, *args):
        """Suppress server logs"""
        pass


def start_file_server():
    """Start a simple HTTP server to serve generated files"""
    try:
        with socketserver.TCPServer((FILE_SERVER_HOST, FILE_SERVER_PORT), FileServerHandler) as httpd:
            logger.info(f"File server running on http://localhost:{FILE_SERVER_PORT}")
            httpd.serve_forever()
    except OSError as e:
        logger.warning(f"File server port {FILE_SERVER_PORT} already in use, skipping...")


# Start file server in background thread
server_thread = threading.Thread(target=start_file_server, daemon=True)
server_thread.start()


def get_file_url(filename: str) -> str:
    """Generate URL for accessing a file"""
    return f"http://localhost:{FILE_SERVER_PORT}/{filename}"


def download_file(url: str) -> str:
    """Download file from URL to temporary location"""
    logger.info(f"Downloading file from: {url}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    
    # Generate temporary filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"downloaded_{timestamp}.xlsx"
    filepath = OUTPUT_DIR / filename
    
    with open(filepath, 'wb') as f:
        f.write(response.content)
    
    logger.info(f"File downloaded to: {filepath}")
    return str(filepath)


@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "rows": {
            "type": "array",
            "description": "List of dictionaries, each representing a row from the Excel file",
            "items": {"type": "object"}
        },
        "headers": {
            "type": "array",
            "description": "List of column names from the Excel file",
            "items": {"type": "string"}
        },
    },
    "required": ["rows", "headers"]
})
def read_excel(file_url: str) -> Dict[str, Any]:
    """
    Read Excel file from URL and convert to Python dict format.
    
    Args:
        file_url: URL or local path to the Excel file
        
    Returns:
        Dictionary containing:
        - rows: List of dictionaries, each representing a row
        - headers: List of column names
    """
    try:
        logger.info(f"Reading Excel file from: {file_url}")
        # Download file if it's a URL
        if file_url.startswith('http://') or file_url.startswith('https://'):
            filepath = download_file(file_url)
        else:
            filepath = file_url
        
        # Read Excel file
        df = pd.read_excel(filepath)
        logger.info(f"Successfully read Excel file with {len(df)} rows and {len(df.columns)} columns")
        
        # Convert to dict format
        headers = df.columns.tolist()
        rows = df.to_dict('records')
        
        # Convert numpy types to Python native types
        rows = convert_numpy_types(rows)
        
        return {
            "rows": rows,
            "headers": headers,
        }
    except Exception as e:
        logger.error(f"Error reading Excel file: {str(e)}")
        return {
            "error": str(e),
            "rows": [],
            "headers": []
        }


@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "filtered_rows": {
            "type": "array",
            "description": "List of dictionaries representing rows that match the filter",
            "items": {"type": "object"}
        },
        "count": {
            "type": "integer",
            "description": "Number of rows that passed the filter"
        }
    },
    "required": ["filtered_rows", "count"]
})
def filter_rows(rows: List[Dict], expression: str) -> Dict[str, Any]:
    """
    Filter rows based on a condition expression.
    
    Args:
        rows: List of row dictionaries
        expression: Filter expression (e.g., "age > 30", "name == 'John'", "price >= 100")
        
    Returns:
        Dictionary containing:
        - filtered_rows: List of rows that match the filter
        - count: Number of filtered rows

    Example:
        expression = "age > 30 and city == 'Beijing'"
    """
    try:
        logger.info(f"Filtering rows with expression: {expression}")
        if not rows:
            logger.warning("No rows to filter")
            return {"filtered_rows": [], "count": 0}
        
        # Convert to DataFrame for easy filtering
        df = pd.DataFrame(rows)
        
        # Apply filter using query
        filtered_df = df.query(expression)
        
        filtered_rows = filtered_df.to_dict('records')
        
        # Convert numpy types to Python native types
        filtered_rows = convert_numpy_types(filtered_rows)
        
        logger.info(f"Filtered {len(rows)} rows to {len(filtered_rows)} rows")
        return {
            "filtered_rows": filtered_rows,
            "count": len(filtered_rows),
            "original_count": len(rows)
        }
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error filtering rows: {str(e)}")
        logger.error(f"Traceback:\n{error_traceback}")
        return {
            "error": str(e),
            "traceback": str(error_traceback),
            "filtered_rows": [],
            "count": 0
        }


@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "result": {
            "type": "array",
            "description": "List of aggregation results. Each item is a dictionary with aggregated values. "
                          "Key naming: "
                          "- With group_by: keys are group column names + original aggregated column names "
                          "- Without group_by: keys are in format '{column}_{operation}' (e.g., 'price_sum', 'quantity_mean')",
            "items": {
                "type": "object",
                "additionalProperties": {
                    "anyOf": [
                        {"type": "number"},
                        {"type": "string"},
                        {"type": "integer"}
                    ]
                },
                "description": "Aggregation result object with dynamic keys based on group_by and aggregation config"
            }
        },
        "count": {
            "type": "integer",
            "description": "Number of result rows"
        }
    },
    "required": ["result", "count"]
})
def aggregate(rows: List[Dict], agg_config: str) -> Dict[str, Any]:
    """
    Perform aggregation operations on data (sum, average, count, groupBy).
    
    Args:
        rows: List of row dictionaries
        agg_config: JSON string with aggregation configuration
                   Format: {"group_by": ["column"], "aggregations": {"column": "operation"}}
                   Operations: sum, mean, count, min, max, std
        
    Returns:
        Dictionary containing:
        - result: List of aggregation results
        - count: Number of result rows
        
    Example:
        agg_config = '{"group_by": ["category"], "aggregations": {"price": "sum", "quantity": "mean"}}'
    """
    try:
        # "Output validation error: 375 is valid under each of {'type': 'integer'}, {'type': 'number'}"
        logger.info(f"Aggregating data with config: {agg_config}")
        if not rows:
            logger.warning("No rows to aggregate")
            return {"error": "No rows to aggregate", "result": []}
        
        # Parse configuration
        config = json.loads(agg_config)
        group_by = config.get("group_by", [])
        aggregations = config.get("aggregations", {})
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        if group_by:
            # Group by aggregation
            grouped = df.groupby(group_by).agg(aggregations).reset_index()
            result = grouped.to_dict('records')
            logger.info(f"Grouped by {group_by}, produced {len(result)} groups")
        else:
            # Overall aggregation
            agg_result = {}
            for col, op in aggregations.items():
                if col in df.columns:
                    if op == "sum":
                        agg_result[f"{col}_{op}"] = df[col].sum()
                    elif op == "mean":
                        agg_result[f"{col}_{op}"] = df[col].mean()
                    elif op == "count":
                        agg_result[f"{col}_{op}"] = df[col].count()
                    elif op == "min":
                        agg_result[f"{col}_{op}"] = df[col].min()
                    elif op == "max":
                        agg_result[f"{col}_{op}"] = df[col].max()
                    elif op == "std":
                        agg_result[f"{col}_{op}"] = df[col].std()
            result = [agg_result]
            logger.info(f"Overall aggregation completed: {result}")
        
        # Convert numpy types to Python native types
        result = convert_numpy_types(result)
        logger.info(f"Converted numpy types result: {result}")
        return {
            "result": result,
            "count": len(result)
        }
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error aggregating data: {str(e)}")
        logger.error(f"Traceback:\n{error_traceback}")
        return {
            "error": str(e),
            "traceback": str(error_traceback),
            "result": []
        }


@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "new_rows": {
            "type": "array",
            "description": "List of row dictionaries with the formula applied (new/modified columns)",
            "items": {"type": "object"}
        },
        "new_column": {
            "type": "string",
            "description": "Name of the new/modified column"
        },
        "count": {
            "type": "integer",
            "description": "Number of rows processed"
        }
    },
    "required": ["new_rows", "count"]
})
def apply_formula(rows: List[Dict], python_expr: str) -> Dict[str, Any]:
    """
    Apply a Python expression to create or modify columns.
    
    Args:
        rows: List of row dictionaries
        python_expr: Python expression to apply (e.g., "total = price * quantity")
        
    Returns:
        Dictionary containing:
        - new_rows: Rows with formula applied
        - new_column: Name of the created/modified column
        - count: Number of rows processed
        
    Example:
        python_expr = "total = price * quantity"
        python_expr = "discount_price = price * 0.9"
    """
    try:
        logger.info(f"Applying formula: {python_expr}")
        if not rows:
            logger.warning("No rows to process")
            return {"error": "No rows to process", "new_rows": []}
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Parse expression (format: "new_col = expression")
        if "=" in python_expr:
            parts = python_expr.split("=", 1)
            new_col = parts[0].strip()
            expression = parts[1].strip()
            
            # Evaluate expression
            df[new_col] = df.eval(expression)
            logger.info(f"Formula applied successfully, created/updated column: {new_col}")
        else:
            logger.error("Invalid expression format")
            return {"error": "Expression must be in format 'new_col = expression'", "new_rows": []}
        
        new_rows = df.to_dict('records')
        
        # Convert numpy types to Python native types
        new_rows = convert_numpy_types(new_rows)
        
        return {
            "new_rows": new_rows,
            "new_column": new_col,
            "count": len(new_rows)
        }
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error applying formula: {str(e)}")
        logger.error(f"Traceback:\n{error_traceback}")
        return {
            "error": str(e),
            "traceback": str(error_traceback),
            "new_rows": []
        }


@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "file_url": {
            "type": "string",
            "description": "URL to access the generated chart image"
        }
    },
    "required": ["file_url"]
})
def plot_chart(rows: List[Dict], chart_type: str, x_col: str = None, y_col: str = None, 
               title: str = None, label_col: str = None) -> Dict[str, Any]:
    """
    Generate various types of charts from data and save to local file.
    
    Args:
        rows: List of row dictionaries
        chart_type: Type of chart to generate
                   Options: "line", "bar", "column", "pie", "scatter", "area", "histogram", "box"
        x_col: Column name for X-axis (required for line, bar, column, scatter, area)
        y_col: Column name for Y-axis (required for line, bar, column, scatter, area)
        title: Custom title for the chart (optional, will auto-generate if not provided)
        label_col: Column name for labels (required for pie chart)
        
    Returns:
        Dictionary containing:
        - file_url: URL to access the chart
        
    Chart Types:
        - line: Line chart with markers
        - bar: Horizontal bar chart
        - column: Vertical bar/column chart
        - pie: Pie chart (requires label_col and y_col for values)
        - scatter: Scatter plot
        - area: Area chart
        - histogram: Histogram (only requires y_col)
        - box: Box plot (only requires y_col, supports multiple columns)
    """
    try:
        logger.info(f"Plotting {chart_type} chart")
        if not rows:
            logger.warning("No rows to plot")
            return {"error": "No rows to plot", "file_url": ""}
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Validate chart type
        valid_chart_types = ["line", "bar", "column", "pie", "scatter", "area", "histogram", "box"]
        if chart_type not in valid_chart_types:
            error_msg = f"Invalid chart type: {chart_type}. Valid types: {', '.join(valid_chart_types)}"
            logger.error(error_msg)
            return {"error": error_msg, "file_url": ""}
        
        # Create figure
        plt.figure(figsize=(10, 6))
        
        # Generate chart based on type
        if chart_type == "line":
            if not x_col or not y_col:
                return {"error": "Line chart requires x_col and y_col", "file_url": ""}
            if x_col not in df.columns or y_col not in df.columns:
                return {"error": f"Columns {x_col} or {y_col} not found", "file_url": ""}
            
            plt.plot(df[x_col], df[y_col], marker='o', linestyle='-', linewidth=2, markersize=6)
            plt.xlabel(x_col, fontsize=12)
            plt.ylabel(y_col, fontsize=12)
            plt.title(title or f'{y_col} vs {x_col}', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha='right')
            
        elif chart_type == "bar":
            if not x_col or not y_col:
                return {"error": "Bar chart requires x_col and y_col", "file_url": ""}
            if x_col not in df.columns or y_col not in df.columns:
                return {"error": f"Columns {x_col} or {y_col} not found", "file_url": ""}
            
            plt.barh(df[x_col], df[y_col], color='steelblue')
            plt.xlabel(y_col, fontsize=12)
            plt.ylabel(x_col, fontsize=12)
            plt.title(title or f'{y_col} by {x_col}', fontsize=14)
            plt.grid(True, axis='x', alpha=0.3)
            
        elif chart_type == "column":
            if not x_col or not y_col:
                return {"error": "Column chart requires x_col and y_col", "file_url": ""}
            if x_col not in df.columns or y_col not in df.columns:
                return {"error": f"Columns {x_col} or {y_col} not found", "file_url": ""}
            
            plt.bar(df[x_col], df[y_col], color='steelblue', width=0.6)
            plt.xlabel(x_col, fontsize=12)
            plt.ylabel(y_col, fontsize=12)
            plt.title(title or f'{y_col} by {x_col}', fontsize=14)
            plt.grid(True, axis='y', alpha=0.3)
            plt.xticks(rotation=45, ha='right')
            
        elif chart_type == "pie":
            if not label_col or not y_col:
                return {"error": "Pie chart requires label_col and y_col", "file_url": ""}
            if label_col not in df.columns or y_col not in df.columns:
                return {"error": f"Columns {label_col} or {y_col} not found", "file_url": ""}
            
            # Create pie chart
            colors = plt.cm.Set3(range(len(df)))
            plt.pie(df[y_col], labels=df[label_col], autopct='%1.1f%%', 
                   startangle=90, colors=colors)
            plt.title(title or f'{y_col} Distribution by {label_col}', fontsize=14)
            plt.axis('equal')
            
        elif chart_type == "scatter":
            if not x_col or not y_col:
                return {"error": "Scatter plot requires x_col and y_col", "file_url": ""}
            if x_col not in df.columns or y_col not in df.columns:
                return {"error": f"Columns {x_col} or {y_col} not found", "file_url": ""}
            
            plt.scatter(df[x_col], df[y_col], alpha=0.6, s=60, color='steelblue', edgecolors='black')
            plt.xlabel(x_col, fontsize=12)
            plt.ylabel(y_col, fontsize=12)
            plt.title(title or f'{y_col} vs {x_col}', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha='right')
            
        elif chart_type == "area":
            if not x_col or not y_col:
                return {"error": "Area chart requires x_col and y_col", "file_url": ""}
            if x_col not in df.columns or y_col not in df.columns:
                return {"error": f"Columns {x_col} or {y_col} not found", "file_url": ""}
            
            plt.fill_between(df[x_col], df[y_col], alpha=0.4, color='steelblue')
            plt.plot(df[x_col], df[y_col], linewidth=2, color='steelblue')
            plt.xlabel(x_col, fontsize=12)
            plt.ylabel(y_col, fontsize=12)
            plt.title(title or f'{y_col} vs {x_col}', fontsize=14)
            plt.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha='right')
            
        elif chart_type == "histogram":
            if not y_col:
                return {"error": "Histogram requires y_col", "file_url": ""}
            if y_col not in df.columns:
                return {"error": f"Column {y_col} not found", "file_url": ""}
            
            plt.hist(df[y_col].dropna(), bins=20, color='steelblue', edgecolor='black', alpha=0.7)
            plt.xlabel(y_col, fontsize=12)
            plt.ylabel('Frequency', fontsize=12)
            plt.title(title or f'Distribution of {y_col}', fontsize=14)
            plt.grid(True, axis='y', alpha=0.3)
            
        elif chart_type == "box":
            if not y_col:
                return {"error": "Box plot requires y_col", "file_url": ""}
            
            # Support multiple columns for box plot
            if isinstance(y_col, str):
                cols_to_plot = [y_col]
            else:
                cols_to_plot = y_col
            
            # Validate columns exist
            missing_cols = [col for col in cols_to_plot if col not in df.columns]
            if missing_cols:
                return {"error": f"Columns not found: {', '.join(missing_cols)}", "file_url": ""}
            
            # Create box plot
            df[cols_to_plot].boxplot()
            plt.ylabel('Value', fontsize=12)
            plt.title(title or f'Box Plot of {", ".join(cols_to_plot)}', fontsize=14)
            plt.grid(True, axis='y', alpha=0.3)
            plt.xticks(rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{chart_type}chart_{timestamp}.png"
        filepath = OUTPUT_DIR / filename
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"{chart_type.capitalize()} chart saved to: {filepath}")
        
        file_url = get_file_url(filename)
        
        result = {
            "file_url": file_url,
        }
            
        return result
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error plotting {chart_type} chart: {str(e)}")
        logger.error(f"Traceback:\n{error_traceback}")
        return {
            "error": str(e),
            "traceback": str(error_traceback),
            "file_url": ""
        }



@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "file_url": {
            "type": "string",
            "description": "URL to download the Excel file"
        },
        "local_path": {
            "type": "string",
            "description": "Local file path of the exported Excel"
        },
        "row_count": {
            "type": "integer",
            "description": "Number of rows exported"
        },
        "columns": {
            "type": "array",
            "description": "List of column names in the exported file",
            "items": {"type": "string"}
        }
    },
    "required": ["file_url", "row_count"]
})
def export_excel(rows: List[Dict]) -> Dict[str, Any]:
    """
    Export processed data to Excel file and return URL for download.
    
    Args:
        rows: List of row dictionaries to export
        
    Returns:
        Dictionary containing:
        - file_url: URL to download the Excel file
        - local_path: Local file path
        - row_count: Number of rows exported
        - columns: Column names
    """
    try:
        logger.info(f"Exporting {len(rows)} rows to Excel")
        if not rows:
            logger.warning("No rows to export")
            return {"error": "No rows to export", "file_url": ""}
        
        # Convert to DataFrame
        df = pd.DataFrame(rows)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"export_{timestamp}.xlsx"
        filepath = OUTPUT_DIR / filename
        
        # Export to Excel
        df.to_excel(filepath, index=False, engine='openpyxl')
        
        logger.info(f"Excel file exported to: {filepath}")
        
        file_url = get_file_url(filename)
        
        return {
            "file_url": file_url,
            "local_path": str(filepath),
            "rows_exported": len(rows),
            "columns": df.columns.tolist()
        }
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Error exporting Excel: {str(e)}")
        logger.error(f"Traceback:\n{error_traceback}")
        return {
            "error": str(e),
            "traceback": str(error_traceback),
            "file_url": ""
        }


# Example usage / test
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Excel Data Processing MCP Server")
    logger.info("=" * 60)
    logger.info("Available Tools:")
    logger.info("1. read_excel - Read Excel file from URL")
    logger.info("2. filter_rows - Filter rows by condition")
    logger.info("3. aggregate - Aggregate data (sum, mean, etc.)")
    logger.info("4. apply_formula - Apply formula to columns")
    logger.info("5. plot_chart - Generate charts (line/bar/column/pie/scatter/area/histogram/box)")
    logger.info("6. export_excel - Export data to Excel")
    logger.info(f"File server: http://localhost:{FILE_SERVER_PORT}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info("=" * 60)
    
    # Run the server
    logger.info("Starting MCP server on port 8003...")
    mcp.run(transport="sse", port=8003)
