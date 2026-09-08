from typing import List, Dict, Any, Optional
import json
import oracledb
import yaml
from pathlib import Path
from datetime import datetime
import uuid


class OraDBEventLogger:
    """Oracle DB Event Logger for tracking all system events and A2A interactions"""
    
    def __init__(self):
        """Initialize Oracle DB Event Logger"""
        # Load Oracle DB credentials from config.yaml
        credentials = self._load_config()
        
        username = credentials.get("ORACLE_DB_USERNAME", "ADMIN")
        password = credentials.get("ORACLE_DB_PASSWORD", "")
        dsn = credentials.get("ORACLE_DB_DSN", "")
        wallet_path = credentials.get("ORACLE_DB_WALLET_LOCATION")
        wallet_password = credentials.get("ORACLE_DB_WALLET_PASSWORD")
        
        if not password or not dsn:
            raise ValueError("Oracle DB credentials not found in config.yaml. Please set ORACLE_DB_USERNAME, ORACLE_DB_PASSWORD, and ORACLE_DB_DSN.")

        # Connect to the database
        try:
            if not wallet_path:
                print(f'[EventLogger] Connecting (no wallet) to dsn {dsn} and user {username}')
                conn = oracledb.connect(user=username, password=password, dsn=dsn)
            else:
                print(f'[EventLogger] Connecting (with wallet) to dsn {dsn} and user {username}')
                conn = oracledb.connect(user=username, password=password, dsn=dsn, 
                                       config_dir=wallet_path, wallet_location=wallet_path, wallet_password=wallet_password)
            print("[EventLogger] Oracle DB Connection successful!")
        except Exception as e:
            print(f"[EventLogger] Oracle DB Connection failed! {e}")
            raise

        self.connection = conn
        self.cursor = conn.cursor()
        
        # Create tables for event logging
        self._create_tables()
    
    def _load_config(self) -> Dict[str, str]:
        """Load configuration from config.yaml"""
        try:
            config_path = Path("config.yaml")
            if not config_path.exists():
                print("[EventLogger] Warning: config.yaml not found. Using empty configuration.")
                return {}
                
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config if config else {}
        except Exception as e:
            print(f"[EventLogger] Warning: Error loading config: {str(e)}")
            return {}
    
    def _create_tables(self):
        """Create tables for storing events"""
        
        # A2A Events Table - tracks all A2A agent interactions
        sql_a2a_events = """
        CREATE TABLE IF NOT EXISTS A2A_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            agent_id VARCHAR2(500),
            agent_name VARCHAR2(500),
            method VARCHAR2(100),
            system_prompt CLOB,
            user_prompt CLOB,
            response CLOB,
            metadata CLOB,
            duration_ms NUMBER,
            status VARCHAR2(50)
        )
        """
        
        # API Events Table - tracks all REST API calls
        sql_api_events = """
        CREATE TABLE IF NOT EXISTS API_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            endpoint VARCHAR2(500),
            method VARCHAR2(20),
            request_data CLOB,
            response_data CLOB,
            status_code NUMBER,
            duration_ms NUMBER,
            user_agent VARCHAR2(500),
            client_ip VARCHAR2(100)
        )
        """
        
        # Model Inference Events Table - tracks all LLM inferences
        sql_model_events = """
        CREATE TABLE IF NOT EXISTS MODEL_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            model_name VARCHAR2(200),
            model_type VARCHAR2(100),
            system_prompt CLOB,
            user_prompt CLOB,
            response CLOB,
            collection_used VARCHAR2(200),
            use_cot NUMBER(1),
            tokens_used NUMBER,
            duration_ms NUMBER,
            context_chunks NUMBER
        )
        """
        
        # Document Processing Events Table - tracks document uploads and processing
        sql_doc_events = """
        CREATE TABLE IF NOT EXISTS DOCUMENT_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            document_type VARCHAR2(50),
            document_id VARCHAR2(200),
            source VARCHAR2(1000),
            chunks_processed NUMBER,
            processing_time_ms NUMBER,
            status VARCHAR2(50),
            error_message CLOB
        )
        """
        
        # Query Events Table - tracks vector store queries
        sql_query_events = """
        CREATE TABLE IF NOT EXISTS QUERY_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            query_text CLOB,
            collection_name VARCHAR2(200),
            results_count NUMBER,
            query_time_ms NUMBER,
            metadata CLOB
        )
        """

        # Reasoning Events Table - tracks reasoning ensemble executions
        sql_reasoning_events = """
        CREATE TABLE IF NOT EXISTS REASONING_EVENTS (
            event_id VARCHAR2(100) PRIMARY KEY,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            query_text CLOB,
            strategies_requested CLOB,
            strategies_completed CLOB,
            winner_strategy VARCHAR2(50),
            winner_response CLOB,
            vote_count NUMBER,
            total_strategies NUMBER,
            similarity_threshold NUMBER,
            all_responses CLOB,
            rag_enabled NUMBER(1),
            collection_used VARCHAR2(200),
            chunks_retrieved NUMBER,
            total_duration_ms NUMBER,
            parallel_execution NUMBER(1),
            config_json CLOB,
            status VARCHAR2(50),
            error_message CLOB
        )
        """

        try:
            self.cursor.execute(sql_a2a_events)
            self.cursor.execute(sql_api_events)
            self.cursor.execute(sql_model_events)
            self.cursor.execute(sql_doc_events)
            self.cursor.execute(sql_query_events)
            self.cursor.execute(sql_reasoning_events)
            self.connection.commit()
            print("[EventLogger] Event logging tables created/verified successfully")
        except Exception as e:
            print(f"[EventLogger] Error creating tables: {str(e)}")
            raise
    
    def log_a2a_event(
        self,
        agent_id: str,
        agent_name: str,
        method: str,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        response: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        status: str = "success"
    ) -> str:
        """Log an A2A agent interaction event"""
        event_id = f"a2a_{uuid.uuid4().hex}"
        
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            sql = """
            INSERT INTO A2A_EVENTS 
            (event_id, agent_id, agent_name, method, system_prompt, user_prompt, 
             response, metadata, duration_ms, status)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10)
            """
            
            self.cursor.execute(sql, (
                event_id,
                agent_id,
                agent_name,
                method,
                system_prompt,
                user_prompt,
                response,
                metadata_json,
                duration_ms,
                status
            ))
            self.connection.commit()
            
            print(f"[EventLogger] A2A event logged: {event_id} - {agent_name} - {method}")
            return event_id
            
        except Exception as e:
            print(f"[EventLogger] Error logging A2A event: {str(e)}")
            return event_id
    
    def log_api_event(
        self,
        endpoint: str,
        method: str,
        request_data: Optional[Dict[str, Any]] = None,
        response_data: Optional[Dict[str, Any]] = None,
        status_code: int = 200,
        duration_ms: Optional[float] = None,
        user_agent: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> str:
        """Log an API endpoint call event"""
        event_id = f"api_{uuid.uuid4().hex}"
        
        try:
            request_json = json.dumps(request_data) if request_data else None
            response_json = json.dumps(response_data) if response_data else None
            
            sql = """
            INSERT INTO API_EVENTS 
            (event_id, endpoint, method, request_data, response_data, 
             status_code, duration_ms, user_agent, client_ip)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9)
            """
            
            self.cursor.execute(sql, (
                event_id,
                endpoint,
                method,
                request_json,
                response_json,
                status_code,
                duration_ms,
                user_agent,
                client_ip
            ))
            self.connection.commit()
            
            print(f"[EventLogger] API event logged: {event_id} - {method} {endpoint}")
            return event_id
            
        except Exception as e:
            print(f"[EventLogger] Error logging API event: {str(e)}")
            return event_id
    
    def log_model_event(
        self,
        model_name: str,
        model_type: str,
        system_prompt: Optional[str] = None,
        user_prompt: Optional[str] = None,
        response: Optional[str] = None,
        collection_used: Optional[str] = None,
        use_cot: bool = False,
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None,
        context_chunks: Optional[int] = None
    ) -> str:
        """Log a model inference event"""
        event_id = f"model_{uuid.uuid4().hex}"
        
        try:
            sql = """
            INSERT INTO MODEL_EVENTS 
            (event_id, model_name, model_type, system_prompt, user_prompt, 
             response, collection_used, use_cot, tokens_used, duration_ms, context_chunks)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)
            """
            
            self.cursor.execute(sql, (
                event_id,
                model_name,
                model_type,
                system_prompt,
                user_prompt,
                response,
                collection_used,
                1 if use_cot else 0,
                tokens_used,
                duration_ms,
                context_chunks
            ))
            self.connection.commit()
            
            print(f"[EventLogger] Model event logged: {event_id} - {model_name}")
            return event_id
            
        except Exception as e:
            print(f"[EventLogger] Error logging model event: {str(e)}")
            return event_id
    
    def log_document_event(
        self,
        document_type: str,
        document_id: str,
        source: str,
        chunks_processed: int,
        processing_time_ms: Optional[float] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Log a document processing event"""
        event_id = f"doc_{uuid.uuid4().hex}"
        
        try:
            sql = """
            INSERT INTO DOCUMENT_EVENTS 
            (event_id, document_type, document_id, source, chunks_processed, 
             processing_time_ms, status, error_message)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
            """
            
            self.cursor.execute(sql, (
                event_id,
                document_type,
                document_id,
                source,
                chunks_processed,
                processing_time_ms,
                status,
                error_message
            ))
            self.connection.commit()
            
            print(f"[EventLogger] Document event logged: {event_id} - {document_type}")
            return event_id
            
        except Exception as e:
            print(f"[EventLogger] Error logging document event: {str(e)}")
            return event_id
    
    def log_query_event(
        self,
        query_text: str,
        collection_name: str,
        results_count: int,
        query_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log a vector store query event"""
        event_id = f"query_{uuid.uuid4().hex}"
        
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            sql = """
            INSERT INTO QUERY_EVENTS 
            (event_id, query_text, collection_name, results_count, query_time_ms, metadata)
            VALUES (:1, :2, :3, :4, :5, :6)
            """
            
            self.cursor.execute(sql, (
                event_id,
                query_text,
                collection_name,
                results_count,
                query_time_ms,
                metadata_json
            ))
            self.connection.commit()
            
            print(f"[EventLogger] Query event logged: {event_id} - {collection_name}")
            return event_id
            
        except Exception as e:
            print(f"[EventLogger] Error logging query event: {str(e)}")
            return event_id

    def log_reasoning_event(
        self,
        query_text: str,
        strategies_requested: List[str],
        winner_strategy: str,
        winner_response: str,
        vote_count: int,
        all_responses: List[Dict[str, Any]],
        rag_enabled: bool = False,
        collection_used: Optional[str] = None,
        chunks_retrieved: int = 0,
        total_duration_ms: Optional[float] = None,
        config: Optional[Dict[str, Any]] = None,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Log a reasoning ensemble execution event"""
        event_id = f"reasoning_{uuid.uuid4().hex}"

        try:
            strategies_json = json.dumps(strategies_requested)
            all_responses_json = json.dumps(all_responses)
            config_json = json.dumps(config) if config else None

            sql = """
            INSERT INTO REASONING_EVENTS
            (event_id, query_text, strategies_requested, winner_strategy, winner_response,
             vote_count, total_strategies, all_responses, rag_enabled, collection_used,
             chunks_retrieved, total_duration_ms, parallel_execution, config_json, status, error_message)
            VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11, :12, :13, :14, :15, :16)
            """

            self.cursor.execute(sql, (
                event_id,
                query_text,
                strategies_json,
                winner_strategy,
                winner_response,
                vote_count,
                len(strategies_requested),
                all_responses_json,
                1 if rag_enabled else 0,
                collection_used,
                chunks_retrieved,
                total_duration_ms,
                1,  # parallel_execution always true for ensemble
                config_json,
                status,
                error_message
            ))
            self.connection.commit()

            print(f"[EventLogger] Reasoning event logged: {event_id} - {winner_strategy}")
            return event_id

        except Exception as e:
            print(f"[EventLogger] Error logging reasoning event: {str(e)}")
            return event_id

    def get_events(
        self,
        event_type: str = "all",
        limit: int = 100,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get events from the database"""

        table_map = {
            "a2a": "A2A_EVENTS",
            "api": "API_EVENTS",
            "model": "MODEL_EVENTS",
            "document": "DOCUMENT_EVENTS",
            "query": "QUERY_EVENTS",
            "reasoning": "REASONING_EVENTS"
        }

        if event_type == "all":
            # Union all tables
            events = []
            for table_name in table_map.values():
                sql = f"SELECT * FROM {table_name} ORDER BY TIMESTAMP DESC FETCH FIRST {limit} ROWS ONLY"
                self.cursor.execute(sql)
                rows = self.cursor.fetchall()
                columns = [desc[0] for desc in self.cursor.description]
                
                for row in rows:
                    event = dict(zip(columns, row))
                    event['event_type'] = table_name.replace('_EVENTS', '').lower()
                    events.append(event)
            
            # Sort by timestamp and limit
            events.sort(key=lambda x: x.get('TIMESTAMP', datetime.min), reverse=True)
            return events[:limit]
        else:
            table_name = table_map.get(event_type)
            if not table_name:
                return []
            
            sql = f"SELECT * FROM {table_name} ORDER BY TIMESTAMP DESC FETCH FIRST {limit} ROWS ONLY"
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            columns = [desc[0] for desc in self.cursor.description]
            
            events = []
            for row in rows:
                event = dict(zip(columns, row))
                event['event_type'] = event_type
                events.append(event)
            
            return events
    
    def get_event_count(self, event_type: str = "all") -> int:
        """Get count of events"""

        table_map = {
            "a2a": "A2A_EVENTS",
            "api": "API_EVENTS",
            "model": "MODEL_EVENTS",
            "document": "DOCUMENT_EVENTS",
            "query": "QUERY_EVENTS",
            "reasoning": "REASONING_EVENTS"
        }

        if event_type == "all":
            total = 0
            for table_name in table_map.values():
                sql = f"SELECT COUNT(*) FROM {table_name}"
                self.cursor.execute(sql)
                count = self.cursor.fetchone()[0]
                total += count
            return total
        else:
            table_name = table_map.get(event_type)
            if not table_name:
                return 0
            
            sql = f"SELECT COUNT(*) FROM {table_name}"
            self.cursor.execute(sql)
            return self.cursor.fetchone()[0]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about logged events"""
        stats = {
            "total_events": self.get_event_count("all"),
            "a2a_events": self.get_event_count("a2a"),
            "api_events": self.get_event_count("api"),
            "model_events": self.get_event_count("model"),
            "document_events": self.get_event_count("document"),
            "query_events": self.get_event_count("query"),
            "reasoning_events": self.get_event_count("reasoning")
        }
        
        # Get average response times for A2A events
        try:
            sql = "SELECT AVG(duration_ms) FROM A2A_EVENTS WHERE duration_ms IS NOT NULL"
            self.cursor.execute(sql)
            avg_a2a_duration = self.cursor.fetchone()[0]
            stats["avg_a2a_duration_ms"] = float(avg_a2a_duration) if avg_a2a_duration else 0
        except Exception:
            stats["avg_a2a_duration_ms"] = 0

        # Get average response times for model events
        try:
            sql = "SELECT AVG(duration_ms) FROM MODEL_EVENTS WHERE duration_ms IS NOT NULL"
            self.cursor.execute(sql)
            avg_model_duration = self.cursor.fetchone()[0]
            stats["avg_model_duration_ms"] = float(avg_model_duration) if avg_model_duration else 0
        except Exception:
            stats["avg_model_duration_ms"] = 0

        # Get most used models
        try:
            sql = """
            SELECT model_name, COUNT(*) as count
            FROM MODEL_EVENTS
            GROUP BY model_name
            ORDER BY count DESC
            FETCH FIRST 5 ROWS ONLY
            """
            self.cursor.execute(sql)
            rows = self.cursor.fetchall()
            stats["top_models"] = [{"model": row[0], "count": row[1]} for row in rows]
        except Exception:
            stats["top_models"] = []
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        print("[EventLogger] Database connection closed")


if __name__ == "__main__":
    # Test the event logger
    logger = OraDBEventLogger()
    
    # Test logging different event types
    print("\n=== Testing Event Logger ===\n")
    
    # Test A2A event
    logger.log_a2a_event(
        agent_id="test_agent_001",
        agent_name="Test RAG Agent",
        method="document.query",
        system_prompt="You are a helpful AI assistant.",
        user_prompt="What is machine learning?",
        response="Machine learning is...",
        metadata={"collection": "general_knowledge"},
        duration_ms=1234.5,
        status="success"
    )
    
    # Test API event
    logger.log_api_event(
        endpoint="/query",
        method="POST",
        request_data={"query": "test query", "use_cot": False},
        response_data={"answer": "test answer"},
        status_code=200,
        duration_ms=567.8
    )
    
    logger.log_model_event(
        model_name="gemma3:270m",
        model_type="ollama",
        user_prompt="What is AI?",
        response="AI is artificial intelligence...",
        collection_used="general_knowledge",
        use_cot=False,
        duration_ms=890.1,
        context_chunks=3
    )
    
    # Get statistics
    print("\n=== Event Statistics ===")
    stats = logger.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Get recent events
    print("\n=== Recent Events ===")
    events = logger.get_events(event_type="all", limit=5)
    for event in events:
        print(f"{event.get('event_type')}: {event.get('EVENT_ID')}")
    
    logger.close()

