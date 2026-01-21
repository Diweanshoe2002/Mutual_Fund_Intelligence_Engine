"""
Main Application Entry Point
Fund Portfolio Intelligence System
"""

import uuid
import logging
from typing import Optional, Dict

from langchain_neo4j import GraphCypherQAChain, Neo4jGraph
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.agents.query_router import IntelligentQueryRouter, GraphPlanner
from src.utils.config import get_settings, get_neo4j_config, get_database_config
from src.database.sql_tools import get_all_tools
from langchain_groq import ChatGroq

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FundIntelligenceSystem:
    """Main system orchestrating SQL and Graph database agents"""
    
    def __init__(self):
        """Initialize the intelligence system"""
        logger.info("Initializing Fund Intelligence System...")
        
        # Load configuration
        self.settings = get_settings()
        
        # Initialize LLM
        self.llm = ChatGroq(
            model=self.settings.groq_model,
            api_key=self.settings.groq_api_key,
            temperature=self.settings.groq_temperature
        )
        
        # Initialize query router
        self.router = IntelligentQueryRouter()
        
        # Initialize databases
        self._init_sql_database()
        self._init_graph_database()
        
        # Initialize agents
        self._init_sql_agent()
        self._init_graph_agent()
        
        logger.info("✅ System initialized successfully")
    
    def _init_sql_database(self):
        """Initialize SQL database connection"""
        db_config = get_database_config()
        db_path = str(db_config.sqlite_path)
        
        self.sql_db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
        logger.info(f"✅ Connected to SQLite: {db_path}")
    
    def _init_graph_database(self):
        """Initialize Neo4j graph database"""
        neo4j_config = get_neo4j_config()
        
        self.graph_db = Neo4jGraph(
            url=neo4j_config.url,
            username=neo4j_config.username,
            password=neo4j_config.password,
            enhanced_schema=True,
        )
        self.graph_db.refresh_schema()
        
        logger.info("✅ Connected to Neo4j")
        logger.info(f"Graph Schema:\n{self.graph_db.schema[:500]}...")
    
    def _init_sql_agent(self):
        """Initialize SQL agent with tools"""
        # Get all tools (SQL toolkit + custom tools)
        all_tools = get_all_tools(self.sql_db, self.llm)
        
        # System prompt for SQL agent
        sql_system_prompt = """
        You are an agent designed to interact with a SQL database.
        Given an input question, create a syntactically correct {dialect} query to run,
        then look at the results of the query and return the answer.
        
        Unless the user specifies a specific number of examples they wish to obtain,
        always limit your query to at most {top_k} results.
        
        You can order the results by a relevant column to return the most interesting
        examples in the database.
        
        Never query for all the columns from a specific table, only ask for the
        relevant columns given the question.
        
        You MUST double check your query before executing it. If you get an error
        while executing a query, rewrite the query and try again.
        
        DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.) to the database.
        
        To start you should ALWAYS look at the tables in the database to see what you
        can query. Do NOT skip this step.
        
        Then you should query the schema of the most relevant tables.
        """.format(
            dialect=self.sql_db.dialect,
            top_k=self.settings.top_k_results,
        )
        
        # Create agent with checkpoint
        self.checkpointer = InMemorySaver()
        self.sql_agent = create_agent(
            self.llm,
            all_tools,
            system_prompt=sql_system_prompt,
            checkpointer=self.checkpointer,
        )
        
        logger.info("✅ SQL Agent initialized")
    
    def _init_graph_agent(self):
        """Initialize Graph database agent"""
        self.graph_agent = GraphCypherQAChain.from_llm(
            llm=self.llm,
            graph=self.graph_db,
            validate_cypher=True,
            verbose=True,
            allow_dangerous_requests=True
        )
        
        self.graph_planner = GraphPlanner()
        
        logger.info("✅ Graph Agent initialized")
    
    def query(self, question: str, thread_id: Optional[str] = None) -> Dict:
        """
        Execute a query using intelligent routing
        
        Args:
            question: User's question
            thread_id: Optional thread ID for conversation tracking
            
        Returns:
            Dictionary with query results and metadata
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing Query: {question}")
        logger.info(f"{'='*60}")
        
        # Route the query
        route = self.router.route(question)
        
        # Generate thread ID if not provided
        if thread_id is None:
            thread_id = str(uuid.uuid4())
        
        # Execute based on route
        if route == "SQL":
            return self._execute_sql_query(question, thread_id)
        else:
            return self._execute_graph_query(question)
    
    def _execute_sql_query(self, question: str, thread_id: str) -> Dict:
        """Execute SQL agent query"""
        logger.info("🗄️ Executing SQL Agent...")
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            result = self.sql_agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
                config=config
            )
            
            # Handle human-in-the-loop if needed
            if result.get('__interrupt__'):
                logger.info("⏸️ Human approval required")
                # In production, implement approval workflow
                # For now, auto-approve
                result = self.sql_agent.invoke(
                    {"messages": [{"role": "user", "content": question}]},
                    config=config
                )
            
            answer = result['messages'][-1].content
            
            logger.info(f"\n{'='*60}")
            logger.info("SQL Query Result:")
            logger.info(f"{'='*60}")
            logger.info(answer)
            logger.info(f"{'='*60}\n")
            
            return {
                "route": "SQL",
                "question": question,
                "answer": answer,
                "thread_id": thread_id
            }
            
        except Exception as e:
            logger.error(f"❌ SQL execution error: {e}")
            return {
                "route": "SQL",
                "question": question,
                "error": str(e)
            }
    
    def _execute_graph_query(self, question: str) -> Dict:
        """Execute Graph database query"""
        logger.info("🕸️ Executing GraphDB Chain...")
        
        try:
            # Plan the query
            planned_question = self.graph_planner.plan(
                question,
                self.graph_db.schema
            )
            
            # Execute query
            result = self.graph_agent.invoke({"query": planned_question})
            
            logger.info(f"\n{'='*60}")
            logger.info("GraphDB Query Result:")
            logger.info(f"{'='*60}")
            logger.info(f"Cypher: {result.get('query', 'N/A')}")
            logger.info(f"Result: {result.get('result', 'N/A')}")
            logger.info(f"{'='*60}\n")
            
            return {
                "route": "GraphDB",
                "question": question,
                "planned_question": planned_question,
                "cypher": result.get('query', 'N/A'),
                "answer": result.get('result', 'N/A')
            }
            
        except Exception as e:
            logger.error(f"❌ Graph execution error: {e}")
            return {
                "route": "GraphDB",
                "question": question,
                "error": str(e)
            }
    
    def batch_query(self, questions: list) -> list:
        """
        Execute multiple queries in batch
        
        Args:
            questions: List of questions
            
        Returns:
            List of results
        """
        results = []
        for question in questions:
            result = self.query(question)
            results.append(result)
        return results


def main():
    """Main execution function"""
    # Initialize system
    system = FundIntelligenceSystem()
    
    # Example queries
    example_queries = [
        "Which AMC has the highest position in HDFC Bank?",
        "List top 5 midcap funds based on last 6 months returns",
        "Show portfolio overlap between funds",
    ]
    
    # Interactive mode
    print("\n" + "="*60)
    print("Fund Portfolio Intelligence System")
    print("="*60)
    print("\nEnter your questions (or 'quit' to exit):\n")
    
    while True:
        try:
            question = input("\n💬 Question: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            if not question:
                continue
            
            # Execute query
            result = system.query(question)
            
            # Display result
            print(f"\n📊 Route: {result['route']}")
            if 'answer' in result:
                print(f"💡 Answer: {result['answer']}")
            elif 'error' in result:
                print(f"❌ Error: {result['error']}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
