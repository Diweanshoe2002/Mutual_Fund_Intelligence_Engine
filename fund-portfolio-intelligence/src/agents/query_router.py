"""
Query Router Module
Intelligent query routing using DSPy for SQL vs GraphDB decisions
"""

import dspy
from typing import Literal
from pydantic import BaseModel, Field

from src.utils.config import get_groq_config


# ============================================
# Routing Models
# ============================================

class RoutingDecision(BaseModel):
    """Decision output from router"""
    route: Literal["SQL", "GraphDB"] = Field(
        description="Chosen execution engine"
    )


class QueryRouter(dspy.Signature):
    """
    Decide whether a user question should be answered using SQL or GraphDB.

    SQL:
    - Mutual fund screening, ranking
    - Returns, alpha, beta, sharpe ratios
    - Benchmark comparison
    - Performance metrics over time periods
    - Fund category analysis

    GraphDB:
    - Latest or historical fund portfolio holdings
    - Fund → Stock relationships
    - Portfolio overlap analysis
    - AMC positioning
    - Stock co-occurrence across funds
    - Asset allocation patterns

    """
    
    question: str = dspy.InputField(desc="User question")
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning")
    decision: RoutingDecision = dspy.OutputField(desc="Final routing decision")


# ============================================
# Router Class
# ============================================

class IntelligentQueryRouter:
    """DSPy-based intelligent query router"""
    
    def __init__(self, config=None):
        """
        Initialize query router
        
        Args:
            config: Optional GroqConfig. If None, loads from settings
        """
        if config is None:
            config = get_groq_config()
        
        # Configure DSPy
        lm = dspy.LM(
            model=f'groq/{config.model}',
            api_key=config.api_key,
            temperature=config.temperature
        )
        dspy.configure(lm=lm)
        
        # Initialize router
        self.router = dspy.Predict(QueryRouter)
    
    def route(self, question: str) -> Literal["SQL", "GraphDB"]:
        """
        Route a query to the appropriate database
        
        Args:
            question: User's query
            
        Returns:
            "SQL" or "GraphDB"
        """
        try:
            result = self.router(question=question)
            
            # Extract decision - handle both model and dict returns
            decision = (
                result.decision.route
                if hasattr(result.decision, "route")
                else result["decision"]["route"]
            )
            
            print(f"📊 Routing Decision: {decision}")
            print(f"💭 Reasoning: {result.reasoning}")
            
            return decision
            
        except Exception as e:
            print(f"⚠️ Router error: {e}, defaulting to SQL")
            return "SQL"
    
    def route_with_explanation(self, question: str) -> dict:
        """
        Route a query and return detailed explanation
        
        Args:
            question: User's query
            
        Returns:
            Dict with route, reasoning, and confidence
        """
        try:
            result = self.router(question=question)
            
            decision = (
                result.decision.route
                if hasattr(result.decision, "route")
                else result["decision"]["route"]
            )
            
            return {
                "route": decision,
                "reasoning": result.reasoning,
                "question": question
            }
            
        except Exception as e:
            return {
                "route": "SQL",
                "reasoning": f"Error during routing: {e}. Defaulting to SQL.",
                "question": question
            }


# ============================================
# Graph Query Planner
# ============================================

class GraphQueryPlan(BaseModel):
    """Planned graph query"""
    refined_question: str = Field(
        description="Graph-focused question aligned to the Neo4j schema"
    )


class GraphQueryPlanner(dspy.Signature):
    """
    You are a Neo4j graph query planner.

    Your task:
    - Understand the user's question
    - Understand the provided Neo4j schema
    - Identify relevant node labels and relationships
    - Rewrite the question so it explicitly matches the schema

    Rules:
    - Focus only on relationships and graph traversal
    - Do NOT include performance metrics (returns, alpha, beta)
    - Do NOT generate Cypher
    """
    
    user_question: str = dspy.InputField(desc="Original user question")
    neo4j_schema: str = dspy.InputField(desc="Neo4j graph schema")
    reasoning: str = dspy.OutputField(desc="Reasoning using the schema")
    plan: GraphQueryPlan = dspy.OutputField(desc="Schema-aligned graph query plan")


class GraphPlanner:
    """Plans graph queries based on Neo4j schema"""
    
    def __init__(self, config=None):
        """Initialize graph planner"""
        if config is None:
            config = get_groq_config()
        
        # Configure DSPy if not already configured
        try:
            lm = dspy.LM(
                model=f'groq/{config.model}',
                api_key=config.api_key,
                temperature=config.temperature
            )
            dspy.configure(lm=lm)
        except:
            pass  # Already configured
        
        self.planner = dspy.Predict(GraphQueryPlanner)
    
    def plan(self, question: str, schema: str) -> str:
        """
        Plan a graph query
        
        Args:
            question: User question
            schema: Neo4j schema string
            
        Returns:
            Refined question aligned to schema
        """
        try:
            result = self.planner(
                user_question=question,
                neo4j_schema=schema
            )
            
            plan = (
                result.plan.refined_question
                if hasattr(result.plan, "refined_question")
                else result["plan"]["refined_question"]
            )
            
            print(f"🎯 Planned Query: {plan}")
            print(f"💭 Planning Reasoning: {result.reasoning}")
            
            return plan
            
        except Exception as e:
            print(f"⚠️ Planning error: {e}, using original question")
            return question


# ============================================
# Main
# ============================================

if __name__ == "__main__":
    # Test the router
    router = IntelligentQueryRouter()
    
    test_questions = [
        "Which AMC has the highest position in HDFC Bank?",
        "List top 5 midcap funds based on last 6 months returns",
        "Show portfolio overlap between Fund A and Fund B",
        "Screen all Large cap funds with good alpha and beta",
        "Which stocks are held by both DSP Focused Fund and ICICI Prudential?"
    ]
    
    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Question: {question}")
        result = router.route_with_explanation(question)
        print(f"Route: {result['route']}")
        print(f"Reasoning: {result['reasoning']}")
