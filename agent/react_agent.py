from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from tools.financial_tools import get_stock_price, get_sentiment_history

# System prompt for agent reasoning
AGENT_SYSTEM_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a financial risk analyst agent for Hong Kong markets.
    
    AVAILABLE TOOLS:
    - get_stock_price: Check price movements
    - get_sentiment_history: Review recent sentiment trends
    
    REASONING PROTOCOL:
    1. Analyze input text for initial sentiment signals
    2. IF negative sentiment detected: call get_sentiment_history to check trend
    3. IF risk signals present: call get_stock_price to assess market reaction
    4. Synthesize findings into final risk assessment
    
    OUTPUT: Always output valid JSON matching RiskAlert schema from models.py
    """),
    ("human", "{input}"),
])

def create_sentinel_agent():
    """Factory function to create the ReAct agent"""
    tools = [get_stock_price, get_sentiment_history]  # Add vector_search_tool when ready
    return create_react_agent(
        model="deepseek-chat",
        tools=tools,
        prompt=AGENT_SYSTEM_PROMPT,
    )