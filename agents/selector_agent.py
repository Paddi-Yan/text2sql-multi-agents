"""
Selector Agent for database schema understanding and dynamic pruning.
LLM-powered intelligent schema selection and pruning.
"""
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from agents.base_agent import BaseAgent
from utils.models import ChatMessage, AgentResponse, DatabaseInfo, DatabaseStats
from storage.mysql_adapter import MySQLAdapter
from services.llm_service import llm_service
from utils.prompts import (
    get_selector_schema_analysis_prompt,
    get_selector_pruning_prompt
)


@dataclass
class SchemaPruningConfig:
    """Configuration for LLM-based schema pruning strategy."""
    complexity_threshold: int = 5  # 1-10 scale
    max_tables_per_query: int = 10
    enable_llm_analysis: bool = True
    fallback_to_simple: bool = True


class DatabaseSchemaManager:
    """Manages database schema information and caching."""
    
    def __init__(self):
        self.db2infos: Dict[str, DatabaseInfo] = {}
        self.db2dbjsons: Dict[str, Dict] = {}
        self.db2stats: Dict[str, DatabaseStats] = {}
        self.mysql_adapter = MySQLAdapter()
    
    def scan_mysql_database_schema(self, db_name: str, db_id: str) -> DatabaseInfo:
        """Scan MySQL database schema information.
        
        Args:
            db_name: MySQL database name
            db_id: Database identifier
            
        Returns:
            DatabaseInfo object with schema details
        """
        if db_id in self.db2infos:
            return self.db2infos[db_id]
        
        try:
            # Create a custom MySQL adapter for this specific database
            from config.settings import DatabaseConfig
            import pymysql
            
            # Get database configuration from environment
            db_config = DatabaseConfig()
            
            # Connect to the specific database
            connection = pymysql.connect(
                host=db_config.host,
                port=db_config.port,
                user=db_config.username,
                password=db_config.password,
                database=db_name,  # Use the specific database name
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            
            cursor = connection.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """, (db_name,))
            
            tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
            
            desc_dict = {}
            value_dict = {}
            pk_dict = {}
            fk_dict = {}
            
            total_columns = 0
            max_columns = 0
            
            for table_name in tables:
                # Get column information
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        COLUMN_COMMENT,
                        COLUMN_KEY
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (db_name, table_name))
                
                columns_info = cursor.fetchall()
                
                # Extract column descriptions
                columns_desc = []
                primary_keys = []
                
                for col_info in columns_info:
                    col_name = col_info['COLUMN_NAME']
                    col_type = col_info['DATA_TYPE']
                    col_comment = col_info['COLUMN_COMMENT'] or ""
                    
                    columns_desc.append((col_name, col_type, col_comment))
                    
                    if col_info['COLUMN_KEY'] == 'PRI':
                        primary_keys.append(col_name)
                
                desc_dict[table_name] = columns_desc
                pk_dict[table_name] = primary_keys
                
                # Get sample values
                try:
                    cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
                    sample_rows = cursor.fetchall()
                    
                    column_values = []
                    for col_info in columns_info:
                        col_name = col_info['COLUMN_NAME']
                        sample_vals = []
                        
                        for row in sample_rows:
                            if col_name in row and row[col_name] is not None:
                                sample_vals.append(str(row[col_name]))
                        
                        column_values.append((col_name, ", ".join(sample_vals[:3])))
                    
                    value_dict[table_name] = column_values
                    
                except Exception as e:
                    # If we can't get sample data, create empty values
                    value_dict[table_name] = [(col[0], "") for col in columns_desc]
                
                # Get foreign keys
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        REFERENCED_TABLE_NAME,
                        REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE 
                    WHERE TABLE_SCHEMA = %s 
                        AND TABLE_NAME = %s 
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                """, (db_name, table_name))
                
                fk_info = cursor.fetchall()
                
                foreign_keys = []
                for fk in fk_info:
                    from_col = fk['COLUMN_NAME']
                    to_table = fk['REFERENCED_TABLE_NAME']
                    to_col = fk['REFERENCED_COLUMN_NAME']
                    foreign_keys.append((from_col, to_table, to_col))
                
                fk_dict[table_name] = foreign_keys
                
                # Update statistics
                col_count = len(columns_desc)
                total_columns += col_count
                max_columns = max(max_columns, col_count)
            
            cursor.close()
            connection.close()
            
            # Create DatabaseInfo
            db_info = DatabaseInfo(
                desc_dict=desc_dict,
                value_dict=value_dict,
                pk_dict=pk_dict,
                fk_dict=fk_dict
            )
            
            # Create DatabaseStats
            db_stats = DatabaseStats(
                table_count=len(tables),
                max_column_count=max_columns,
                total_column_count=total_columns,
                avg_column_count=total_columns / len(tables) if tables else 0
            )
            
            # Cache results
            self.db2infos[db_id] = db_info
            self.db2stats[db_id] = db_stats
            
            # Create JSON representation for caching
            self.db2dbjsons[db_id] = {
                "tables": {
                    table: {
                        "columns": [{"name": col[0], "type": col[1], "description": col[2]} for col in db_info.desc_dict[table]],
                        "primary_keys": db_info.pk_dict[table],
                        "foreign_keys": [{"from": fk[0], "to_table": fk[1], "to_column": fk[2]} for fk in db_info.fk_dict[table]],
                        "sample_values": dict(db_info.value_dict[table])
                    }
                    for table in db_info.desc_dict.keys()
                },
                "statistics": {
                    "table_count": db_stats.table_count,
                    "total_columns": db_stats.total_column_count,
                    "avg_columns": db_stats.avg_column_count
                }
            }
            
            return db_info
            
        except Exception as e:
            raise Exception(f"Failed to scan MySQL database schema: {e}")
    
    def get_database_info(self, db_id: str) -> Optional[DatabaseInfo]:
        """Get cached database info."""
        return self.db2infos.get(db_id)
    
    def get_database_stats(self, db_id: str) -> Optional[DatabaseStats]:
        """Get cached database statistics."""
        return self.db2stats.get(db_id)
    
    def get_database_json(self, db_id: str) -> Optional[Dict]:
        """Get cached database JSON representation."""
        return self.db2dbjsons.get(db_id)


class LLMSchemaPruner:
    """LLM-powered intelligent schema pruning based on query relevance."""
    
    def __init__(self, config: SchemaPruningConfig):
        self.config = config
        import logging
        self.logger = logging.getLogger(f"{__name__}.LLMSchemaPruner")
    
    def analyze_schema_complexity(self, db_id: str, schema_text: str, db_stats: DatabaseStats) -> Dict[str, Any]:
        """Use LLM to analyze schema complexity and determine if pruning is needed.
        
        Args:
            db_id: Database identifier
            schema_text: Full schema description text
            db_stats: Database statistics
            
        Returns:
            Dictionary with analysis results
        """
        if not self.config.enable_llm_analysis:
            return self._simple_complexity_analysis(db_stats)
        
        try:
            # Get LLM analysis prompt
            system_prompt, user_prompt = get_selector_schema_analysis_prompt(
                db_id=db_id,
                schema_info=schema_text,
                table_count=db_stats.table_count,
                total_columns=db_stats.total_column_count,
                avg_columns=db_stats.avg_column_count
            )
            
            # Call LLM for analysis
            response = llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=1000
            )
            
            if response.success:
                # Parse JSON response
                analysis_data = llm_service.extract_json_from_response(response.content)
                if analysis_data:
                    return analysis_data
            
            # Fallback to simple analysis
            return self._simple_complexity_analysis(db_stats)
            
        except Exception as e:
            self.logger.warning(f"LLM schema analysis failed: {e}, using simple fallback")
            return self._simple_complexity_analysis(db_stats)
    
    def prune_schema_with_llm(self, query: str, schema_text: str, fk_info: str, evidence: str = "") -> Dict[str, Any]:
        """Use LLM to prune schema based on query relevance.
        
        Args:
            query: Natural language query
            schema_text: Full schema description text
            fk_info: Foreign key relationships
            evidence: Additional context
            
        Returns:
            Dictionary with pruning decisions for each table
        """
        if not self.config.enable_llm_analysis:
            return {}
        
        try:
            # Get LLM pruning prompt
            system_prompt, user_prompt = get_selector_pruning_prompt(
                query=query,
                schema_info=schema_text,
                fk_info=fk_info,
                evidence=evidence
            )
            
            # Call LLM for pruning decisions
            response = llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.1,
                max_tokens=2000
            )
            
            if response.success:
                # Parse JSON response
                pruning_data = llm_service.extract_json_from_response(response.content)
                if pruning_data and "pruning_decisions" in pruning_data:
                    return pruning_data["pruning_decisions"]
            
            # Fallback: no pruning
            return {}
            
        except Exception as e:
            self.logger.warning(f"LLM schema pruning failed: {e}, using no pruning")
            return {}
    
    def _simple_complexity_analysis(self, db_stats: DatabaseStats) -> Dict[str, Any]:
        """Simple rule-based complexity analysis as fallback."""
        complexity_score = 1
        
        # Basic complexity scoring
        if db_stats.table_count > 10:
            complexity_score += 2
        if db_stats.avg_column_count > 8:
            complexity_score += 2
        if db_stats.total_column_count > 50:
            complexity_score += 3
        
        needs_pruning = complexity_score >= self.config.complexity_threshold
        
        return {
            "needs_pruning": needs_pruning,
            "complexity_score": min(complexity_score, 10),
            "token_estimate": db_stats.total_column_count * 20,  # Rough estimate
            "pruning_strategy": "llm_based" if needs_pruning else "no_pruning",
            "key_tables": [],  # Would need more analysis
            "reasoning": f"Simple analysis: {complexity_score}/10 complexity score"
        }


class SelectorAgent(BaseAgent):
    """Selector agent for database schema understanding and dynamic pruning."""
    
    def __init__(self, agent_name: str = "Selector", tables_json_path: str = "", router=None):
        """Initialize Selector agent.
        
        Args:
            agent_name: Name of the agent
            tables_json_path: Path to tables JSON files (fallback option)
            router: Message router for inter-agent communication
        """
        super().__init__(agent_name, router)
        
        self.tables_json_path = tables_json_path
        self.schema_manager = DatabaseSchemaManager()
        self.pruning_config = SchemaPruningConfig()
        self.schema_pruner = LLMSchemaPruner(self.pruning_config)
        
        # Performance tracking
        self.pruning_stats = {
            "total_queries": 0,
            "pruned_queries": 0,
            "avg_pruning_ratio": 0.0,
            "token_savings": 0
        }
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process message for schema selection and pruning.
        
        Args:
            message: Input message with query and database info
            
        Returns:
            AgentResponse with schema selection results
        """
        if not self._validate_message(message):
            return self._prepare_response(message, success=False, error="Invalid message")
        
        try:
            # Get or scan database schema
            db_info = self._get_database_info(message.db_id)
            if not db_info:
                return self._prepare_response(
                    message, success=False, error=f"Could not load schema for database: {message.db_id}"
                )
            
            # Get database statistics
            db_stats = self.schema_manager.get_database_stats(message.db_id)
            
            # Generate full schema description
            desc_str, fk_str = self._get_db_desc_str(message.db_id, None)
            
            # Use LLM to analyze schema complexity and determine pruning needs
            complexity_analysis = self.schema_pruner.analyze_schema_complexity(
                message.db_id, desc_str, db_stats
            )
            
            need_prune = complexity_analysis.get("needs_pruning", False)
            
            if need_prune:
                # Perform LLM-based schema pruning
                pruning_result = self.schema_pruner.prune_schema_with_llm(
                    query=message.query,
                    schema_text=desc_str,
                    fk_info=fk_str,
                    evidence=message.evidence
                )
                
                if pruning_result:
                    # Generate pruned schema description
                    desc_str, fk_str = self._get_db_desc_str(message.db_id, pruning_result)
                    message.pruned = True
                    message.chosen_db_schema_dict = pruning_result
                    
                    self.pruning_stats["pruned_queries"] += 1
                    self.logger.info(f"Schema pruned for query: {message.query[:50]}...")
                else:
                    message.pruned = False
                    self.logger.info(f"LLM pruning returned no results, keeping full schema")
            else:
                message.pruned = False
                self.logger.info(f"No pruning needed for query: {message.query[:50]}...")
            
            # Update message with schema information
            message.desc_str = desc_str
            message.fk_str = fk_str
            message.extracted_schema = self.schema_manager.get_database_json(message.db_id)
            
            # Route to next agent (Decomposer)
            message.send_to = "Decomposer"
            
            # Update statistics
            self.pruning_stats["total_queries"] += 1
            
            self.logger.info(f"Schema selection completed for {message.db_id}")
            
            return self._prepare_response(
                message, 
                success=True,
                schema_selected=True,
                pruned=message.pruned,
                table_count=db_stats.table_count if db_stats else 0,
                column_count=db_stats.total_column_count if db_stats else 0
            )
            
        except Exception as e:
            self.logger.error(f"Error in schema selection: {e}")
            return self._prepare_response(message, success=False, error=str(e))
    
    def _get_database_info(self, db_id: str) -> Optional[DatabaseInfo]:
        """Get database information, scanning if necessary."""
        # Check cache first
        db_info = self.schema_manager.get_database_info(db_id)
        if db_info:
            return db_info
        
        # Try to scan from MySQL database
        try:
            return self.schema_manager.scan_mysql_database_schema(db_id, db_id)
        except Exception as e:
            self.logger.warning(f"Could not scan MySQL database {db_id}: {e}")
        
        # Fallback: Try to load from JSON file
        if self.tables_json_path:
            json_path = f"{self.tables_json_path}/{db_id}.json"
            try:
                return self._load_schema_from_json(json_path, db_id)
            except Exception as e:
                self.logger.warning(f"Could not load schema from JSON {db_id}: {e}")
        
        return None
    
    def _load_schema_from_json(self, json_path: str, db_id: str) -> DatabaseInfo:
        """Load schema information from JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        desc_dict = {}
        value_dict = {}
        pk_dict = {}
        fk_dict = {}
        
        for table_name, table_info in data.get("tables", {}).items():
            # Extract column descriptions
            columns = table_info.get("columns", [])
            desc_dict[table_name] = [
                (col.get("name", ""), col.get("type", ""), col.get("description", ""))
                for col in columns
            ]
            
            # Extract primary keys
            pk_dict[table_name] = table_info.get("primary_keys", [])
            
            # Extract foreign keys
            fks = table_info.get("foreign_keys", [])
            fk_dict[table_name] = [
                (fk.get("from", ""), fk.get("to_table", ""), fk.get("to_column", ""))
                for fk in fks
            ]
            
            # Extract sample values
            sample_values = table_info.get("sample_values", {})
            value_dict[table_name] = list(sample_values.items())
        
        # Create DatabaseInfo
        db_info = DatabaseInfo(
            desc_dict=desc_dict,
            value_dict=value_dict,
            pk_dict=pk_dict,
            fk_dict=fk_dict
        )
        
        # Cache the result
        self.schema_manager.db2infos[db_id] = db_info
        self.schema_manager.db2dbjsons[db_id] = data
        
        # Calculate and cache statistics
        total_columns = sum(len(cols) for cols in desc_dict.values())
        max_columns = max(len(cols) for cols in desc_dict.values()) if desc_dict else 0
        
        db_stats = DatabaseStats(
            table_count=len(desc_dict),
            max_column_count=max_columns,
            total_column_count=total_columns,
            avg_column_count=total_columns / len(desc_dict) if desc_dict else 0
        )
        
        self.schema_manager.db2stats[db_id] = db_stats
        
        return db_info
    
    def _get_db_desc_str(self, db_id: str, extracted_schema: Optional[Dict[str, Any]]) -> Tuple[str, str]:
        """Generate database description string and foreign key relationships.
        
        Args:
            db_id: Database identifier
            extracted_schema: Optional pruned schema (table -> columns mapping)
            
        Returns:
            Tuple of (description_string, foreign_key_string)
        """
        db_info = self.schema_manager.get_database_info(db_id)
        if not db_info:
            return "", ""
        
        desc_parts = []
        fk_parts = []
        
        # Determine which tables to include
        if extracted_schema:
            tables_to_include = {
                table: columns for table, columns in extracted_schema.items()
                if columns != "drop_all"
            }
        else:
            tables_to_include = {
                table: "keep_all" for table in db_info.desc_dict.keys()
            }
        
        for table_name, column_selection in tables_to_include.items():
            if table_name not in db_info.desc_dict:
                continue
            
            all_columns = db_info.desc_dict[table_name]
            sample_values = dict(db_info.value_dict.get(table_name, []))
            
            # Select columns based on pruning decision
            if column_selection == "keep_all":
                selected_columns = all_columns
            elif isinstance(column_selection, list):
                selected_columns = [
                    col for col in all_columns if col[0] in column_selection
                ]
            else:
                continue
            
            # Build table description
            desc_parts.append(f"# Table: {table_name}")
            desc_parts.append("[")
            
            for col_name, col_type, col_desc in selected_columns:
                col_line = f"  ({col_name}"
                
                if col_type:
                    col_line += f", {col_type}"
                
                # Add sample values if available
                if col_name in sample_values and sample_values[col_name]:
                    col_line += f". Value examples: {sample_values[col_name]}"
                
                if col_desc:
                    col_line += f". {col_desc}"
                
                col_line += "),"
                desc_parts.append(col_line)
            
            # Remove trailing comma from last column
            if desc_parts and desc_parts[-1].endswith(","):
                desc_parts[-1] = desc_parts[-1][:-1]
            
            desc_parts.append("]")
            desc_parts.append("")
        
        # Build foreign key relationships
        for table_name in tables_to_include.keys():
            if table_name in db_info.fk_dict:
                for from_col, to_table, to_col in db_info.fk_dict[table_name]:
                    if to_table in tables_to_include:  # Only include if target table is also included
                        fk_parts.append(f"{table_name}.{from_col} = {to_table}.{to_col}")
        
        desc_str = "\n".join(desc_parts).strip()
        fk_str = "\n".join(fk_parts) if fk_parts else ""
        
        return desc_str, fk_str
    

    
    def get_pruning_stats(self) -> Dict[str, Any]:
        """Get schema pruning statistics.
        
        Returns:
            Dictionary with pruning performance metrics
        """
        if self.pruning_stats["total_queries"] > 0:
            self.pruning_stats["avg_pruning_ratio"] = (
                self.pruning_stats["pruned_queries"] / self.pruning_stats["total_queries"]
            )
        
        return self.pruning_stats.copy()
    
    def reset_pruning_stats(self):
        """Reset pruning statistics."""
        self.pruning_stats = {
            "total_queries": 0,
            "pruned_queries": 0,
            "avg_pruning_ratio": 0.0,
            "token_savings": 0
        }
    
    def update_pruning_config(self, **kwargs):
        """Update pruning configuration.
        
        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.pruning_config, key):
                setattr(self.pruning_config, key, value)
        
        # Recreate pruner with new config
        self.schema_pruner = SchemaPruner(self.pruning_config)
        self.logger.info(f"Updated pruning configuration: {kwargs}")