from langchain_core.tools import tool
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional

@tool
def get_stock_price(stock_code: str, date: Optional[str] = None) -> dict:
    """
    Fetch historical price data for a given HK stock code.
    
    Args:
        stock_code: HK stock code with .HK suffix (e.g., "00700.HK")
        date: Optional date in YYYY-MM-DD format; defaults to latest
    
    Returns:
        dict with keys: close, change_pct, volume, timestamp
    """
    try:
        if date:
            end_date = datetime.strptime(date, "%Y-%m-%d")
            start_date = end_date - timedelta(days=1)
        else:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)
        
        ticker = yf.Ticker(stock_code)
        hist = ticker.history(start=start_date, end=end_date)
        
        if hist.empty:
            return {"error": f"No data found for {stock_code}"}
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        
        return {
            "close": round(latest["Close"], 2),
            "change_pct": round((latest["Close"] - prev["Close"]) / prev["Close"] * 100, 2),
            "volume": int(latest["Volume"]),
            "timestamp": end_date.strftime("%Y-%m-%d")
        }
    except Exception as e:
        return {"error": str(e)}

@tool
def get_sentiment_history(stock_code: str, days: int = 7) -> list:
    """
    Retrieve recent sentiment scores from vector store for trend analysis.
    Requires vector_storage.VectorStore to be initialized.
    """
    # This would integrate with existing vector_storage.py
    # Placeholder for integration
    return []