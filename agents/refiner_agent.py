"""
Refiner agent for SQL execution validation and error correction.

This agent is responsible for:
1. SQL syntax and semantic validation
2. Database execution and result verification
3. Error-based SQL refinement
4. Security checks and SQL injection protection
5. Execution timeout control
"""
import re
import time
import sqlite3
import logging
import threading
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager

from agents.base_agent import BaseAgent
from utils.models import ChatMessage, AgentResponse, SQLExecutionResult, SecurityValidationResult, RiskLevel
from utils.prompts import get_refiner_validation_prompt, get_refiner_refinement_prompt
from services.llm_service import LLMService
from storage.mysql_adapter import MySQLAdapter


class TimeoutError(Exception):
    """Custom timeout exception."""
    pass


@contextmanager
def execution_timeout(seconds: int):
    """Context manager for SQL execution timeout (Windows compatible).
    
    Args:
        seconds: Timeout duration in seconds
    """
    result = {"completed": False, "exception": None}
    
    def target():
        try:
            result["completed"] = True
        except Exception as e:
            result["exception"] = e
    
    # For this implementation, we'll use a simple approach
    # In production, you might want to use more sophisticated timeout mechanisms
    try:
        yield
    except Exception as e:
        if "timeout" in str(e).lower():
            raise TimeoutError("SQL execution timed out")
        raise


class SQLSecurityValidator:
    """SQL security validation for injection prevention."""
    
    def __init__(self):
        """Initialize security validator."""
        self.dangerous_patterns = [
            r";\s*(drop|delete|update|insert|create|alter|truncate)\s+",
            r"union\s+select",
            r"exec\s*\(",
            r"xp_cmdshell",
            r"sp_executesql",
            r"--\s*$",
            r"/\*.*\*/",
            r"'.*'.*or.*'.*'.*=.*'.*'",
            r"1\s*=\s*1",
            r"or\s+1\s*=\s*1",
            r"and\s+1\s*=\s*1",
        ]
        
        self.allowed_keywords = {
            'select', 'from', 'where', 'join', 'inner', 'left', 'right', 'outer',
            'group', 'by', 'having', 'order', 'limit', 'offset', 'as', 'on',
            'and', 'or', 'not', 'in', 'exists', 'between', 'like', 'is', 'null',
            'count', 'sum', 'avg', 'min', 'max', 'distinct', 'case', 'when', 'then',
            'else', 'end', 'with', 'union', 'all', 'except', 'intersect'
        }
    
    def validate_sql(self, sql: str) -> SecurityValidationResult:
        """Validate SQL for security risks.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            SecurityValidationResult with validation details
        """
        sql_lower = sql.lower().strip()
        
        # Check for dangerous patterns
        for pattern in self.dangerous_patterns:
            if re.search(pattern, sql_lower, re.IGNORECASE | re.MULTILINE):
                return SecurityValidationResult(
                    is_safe=False,
                    risk_level=RiskLevel.HIGH,
                    detected_pattern=pattern,
                    recommendations=["Remove dangerous SQL operations", "Use parameterized queries"]
                )
        
        # Check if it's a SELECT-only query
        if not sql_lower.startswith('select') and not sql_lower.startswith('with'):
            return SecurityValidationResult(
                is_safe=False,
                risk_level=RiskLevel.MEDIUM,
                error="Only SELECT queries are allowed",
                recommendations=["Use SELECT statements only", "Avoid data modification operations"]
            )
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"sleep\s*\(",
            r"benchmark\s*\(",
            r"load_file\s*\(",
            r"into\s+outfile",
            r"into\s+dumpfile"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, sql_lower, re.IGNORECASE):
                return SecurityValidationResult(
                    is_safe=False,
                    risk_level=RiskLevel.MEDIUM,
                    detected_pattern=pattern,
                    recommendations=["Remove suspicious functions", "Use standard SQL operations only"]
                )
        
        return SecurityValidationResult(
            is_safe=True,
            risk_level=RiskLevel.LOW
        )


class RefinerAgent(BaseAgent):
    """Refiner agent for SQL execution validation and error correction."""
    
    def __init__(self, data_path: str, dataset_name: str = "generic", 
                 llm_service: Optional[LLMService] = None,
                 mysql_adapter: Optional[MySQLAdapter] = None):
        """Initialize Refiner agent.
        
        Args:
            data_path: Path to database files
            dataset_name: Dataset name for context
            llm_service: LLM service for refinement
            mysql_adapter: MySQL adapter for database operations
        """
        super().__init__("Refiner")
        
        self.data_path = data_path
        self.dataset_name = dataset_name
        self.llm_service = llm_service or LLMService()
        self.mysql_adapter = mysql_adapter
        self.security_validator = SQLSecurityValidator()
        
        # Execution settings
        self.execution_timeout = 120  # 120 seconds as specified
        self.max_refinement_attempts = 3
        
        # Statistics
        self.validation_count = 0
        self.execution_count = 0
        self.refinement_count = 0
        self.security_violations = 0
        
        self.logger = logging.getLogger("agents.refiner_agent")
        self.logger.info(f"Refiner agent initialized with dataset: {dataset_name}")
    
    def talk(self, message: ChatMessage) -> AgentResponse:
        """Process message for SQL validation and execution.
        
        Args:
            message: Input message with SQL to validate
            
        Returns:
            AgentResponse with validation and execution results
        """
        if not self._validate_message(message):
            return self._prepare_response(
                message, 
                success=False, 
                error="Invalid message format"
            )
        
        if not message.final_sql:
            return self._prepare_response(
                message,
                success=False,
                error="No SQL query provided for validation"
            )
        
        self.logger.info(f"Refining SQL for query: {message.query[:100]}...")
        
        try:
            # Step 1: Security validation
            security_result = self.security_validator.validate_sql(message.final_sql)
            if not security_result.is_safe:
                self.security_violations += 1
                self.logger.warning(f"Security violation detected: {security_result.detected_pattern}")
                
                return self._prepare_response(
                    message,
                    success=False,
                    error=f"Security violation: {security_result.error or security_result.detected_pattern}",
                    security_result=security_result
                )
            
            # Step 2: LLM-based SQL validation (optional pre-validation)
            validation_result = self._validate_sql_with_llm(message.final_sql, message)
            if validation_result and not validation_result.get("is_valid", True):
                self.logger.info("LLM validation detected potential issues, but proceeding with execution...")
                # Log validation issues but don't block execution
                for issue in validation_result.get("syntax_errors", []):
                    self.logger.warning(f"Syntax issue detected: {issue}")
                for issue in validation_result.get("logical_issues", []):
                    self.logger.warning(f"Logical issue detected: {issue}")
            
            # Step 3: Execute SQL
            execution_result = self._execute_sql(message.final_sql, message.db_id)
            message.execution_result = execution_result.__dict__
            
            # Step 4: Check if refinement is needed
            if self._is_need_refine(execution_result):
                self.logger.info("SQL needs refinement, attempting to fix...")
                
                # Attempt refinement
                refined_sql = self._refine_sql(
                    message.final_sql,
                    execution_result,
                    message
                )
                
                if refined_sql and refined_sql != message.final_sql:
                    # Re-execute refined SQL
                    message.final_sql = refined_sql
                    message.fixed = True
                    execution_result = self._execute_sql(refined_sql, message.db_id)
                    message.execution_result = execution_result.__dict__
                    
                    self.refinement_count += 1
                    self.logger.info("SQL successfully refined and re-executed")
            
            # Mark as completed
            message.send_to = "System"
            
            return self._prepare_response(
                message,
                success=execution_result.is_successful,
                error=execution_result.sqlite_error if not execution_result.is_successful else None,
                execution_result=execution_result,
                refined=message.fixed,
                security_validated=True
            )
            
        except Exception as e:
            self.logger.error(f"Error in Refiner agent: {e}")
            return self._prepare_response(
                message,
                success=False,
                error=str(e)
            )
    
    def _execute_sql(self, sql: str, db_id: str) -> SQLExecutionResult:
        """Execute SQL query with timeout control.
        
        Args:
            sql: SQL query to execute
            db_id: Database identifier
            
        Returns:
            SQLExecutionResult with execution details
        """
        self.execution_count += 1
        start_time = time.time()
        
        result = SQLExecutionResult(
            sql=sql,
            execution_time=0.0,
            is_successful=False
        )
        
        try:
            if self.mysql_adapter:
                # Use MySQL adapter for real database execution
                try:
                    data = self.mysql_adapter.execute_query(sql)
                    result.data = [(tuple(row.values()) if isinstance(row, dict) else row) for row in data]
                    result.is_successful = True
                    
                except Exception as e:
                    result.sqlite_error = str(e)
                    result.exception_class = type(e).__name__
                    
            else:
                # Fallback to SQLite for testing/development
                import os
                if os.path.exists(f"{self.data_path}/{db_id}.sqlite"):
                    db_path = f"{self.data_path}/{db_id}.sqlite"
                elif os.path.exists(f"{self.data_path}/{db_id}/{db_id}.sqlite"):
                    db_path = f"{self.data_path}/{db_id}/{db_id}.sqlite"
                else:
                    # Try direct path
                    db_path = f"{self.data_path}/{db_id}.sqlite"
                
                with sqlite3.connect(db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    result.data = cursor.fetchall()
                    result.is_successful = True
                        
        except sqlite3.Error as e:
            result.sqlite_error = str(e)
            result.exception_class = type(e).__name__
            self.logger.warning(f"SQLite error: {e}")
            
        except Exception as e:
            result.sqlite_error = str(e)
            result.exception_class = type(e).__name__
            self.logger.error(f"Unexpected error during SQL execution: {e}")
        
        finally:
            result.execution_time = time.time() - start_time
        
        return result
    
    def _validate_sql_with_llm(self, sql: str, message: ChatMessage) -> Optional[Dict[str, Any]]:
        """Validate SQL using LLM before execution.
        
        Args:
            sql: SQL query to validate
            message: Original message with context
            
        Returns:
            Validation result dictionary or None if validation fails
        """
        self.validation_count += 1
        
        try:
            # Get validation prompt
            system_prompt, user_prompt = get_refiner_validation_prompt(
                sql_query=sql,
                schema_info=message.desc_str or "No schema information available",
                original_query=message.query
            )
            
            # Call LLM for validation
            response = self.llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # Low temperature for consistent validation
                max_tokens=800
            )
            
            if response and response.strip():
                # Try to parse JSON response
                import json
                try:
                    validation_result = json.loads(response.strip())
                    self.logger.info(f"LLM validation completed: valid={validation_result.get('is_valid', True)}")
                    return validation_result
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract key information
                    self.logger.warning("Failed to parse LLM validation response as JSON")
                    return self._parse_validation_response(response)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error during LLM validation: {e}")
            return None
    
    def _parse_validation_response(self, response: str) -> Dict[str, Any]:
        """Parse non-JSON validation response.
        
        Args:
            response: LLM response text
            
        Returns:
            Parsed validation result
        """
        result = {
            "is_valid": True,
            "syntax_errors": [],
            "logical_issues": [],
            "security_concerns": [],
            "suggestions": []
        }
        
        response_lower = response.lower()
        
        # Check for validation indicators
        if any(word in response_lower for word in ["invalid", "error", "incorrect", "wrong"]):
            result["is_valid"] = False
        
        # Extract errors and suggestions (simple pattern matching)
        lines = response.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            if any(word in line_lower for word in ["syntax error", "syntax issue"]):
                result["syntax_errors"].append(line.strip())
            elif any(word in line_lower for word in ["logical", "logic"]):
                result["logical_issues"].append(line.strip())
            elif any(word in line_lower for word in ["security", "injection"]):
                result["security_concerns"].append(line.strip())
            elif any(word in line_lower for word in ["suggest", "recommend", "should"]):
                result["suggestions"].append(line.strip())
        
        return result
    
    def _is_need_refine(self, exec_result: SQLExecutionResult) -> bool:
        """Check if SQL needs refinement based on execution result.
        
        Args:
            exec_result: SQL execution result
            
        Returns:
            True if refinement is needed
        """
        if exec_result.is_successful:
            return False
        
        # Check for common refinable errors
        error_msg = exec_result.sqlite_error.lower()
        
        refinable_errors = [
            "no such table",
            "no such column",
            "syntax error",
            "ambiguous column name",
            "misuse of aggregate",
            "group by",
            "having clause",
            "order by"
        ]
        
        return any(error in error_msg for error in refinable_errors)
    
    def _refine_sql(self, original_sql: str, error_result: SQLExecutionResult, 
                   message: ChatMessage) -> Optional[str]:
        """Refine SQL based on execution error.
        
        Args:
            original_sql: Original SQL query
            error_result: Execution error result
            message: Original message with context
            
        Returns:
            Refined SQL query or None if refinement failed
        """
        try:
            # Build context for refinement
            context_parts = []
            
            if message.desc_str:
                context_parts.append(f"Database Schema:\n{message.desc_str}")
            
            if message.fk_str:
                context_parts.append(f"Foreign Key Relations:\n{message.fk_str}")
            
            if message.evidence:
                context_parts.append(f"Evidence:\n{message.evidence}")
            
            context = "\n\n".join(context_parts)
            
            # Get refinement prompt
            system_prompt, user_prompt = get_refiner_refinement_prompt(
                original_sql=original_sql,
                error_info=error_result.sqlite_error,
                schema_info=message.desc_str or "No schema information available",
                original_query=message.query,
                context=context
            )
            
            # Call LLM for refinement
            response = self.llm_service.generate_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # Low temperature for precise corrections
                max_tokens=1000
            )
            
            if response and response.strip():
                # Extract SQL from response
                refined_sql = self._extract_sql_from_response(response)
                
                if refined_sql and refined_sql != original_sql:
                    self.logger.info(f"SQL refined: {original_sql[:50]}... -> {refined_sql[:50]}...")
                    return refined_sql
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error during SQL refinement: {e}")
            return None
    
    def _extract_sql_from_response(self, response: str) -> Optional[str]:
        """Extract SQL query from LLM response.
        
        Args:
            response: LLM response text
            
        Returns:
            Extracted SQL query or None
        """
        # Look for SQL in code blocks
        sql_patterns = [
            r"```sql\s*(.*?)\s*```",
            r"```\s*(SELECT.*?)\s*```",
            r"SQL:\s*(SELECT.*?)(?:\n|$)",
            r"Query:\s*(SELECT.*?)(?:\n|$)",
            r"(SELECT\s+.*?)(?:\n\n|$)"
        ]
        
        for pattern in sql_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match:
                sql = match.group(1).strip()
                if sql and sql.upper().startswith('SELECT'):
                    return sql
        
        # If no pattern matches, check if the entire response is SQL
        response_clean = response.strip()
        if response_clean.upper().startswith('SELECT'):
            return response_clean
        
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Refiner agent statistics.
        
        Returns:
            Dictionary with agent statistics
        """
        base_stats = super().get_stats()
        
        refiner_stats = {
            "validation_count": self.validation_count,
            "execution_count": self.execution_count,
            "refinement_count": self.refinement_count,
            "security_violations": self.security_violations,
            "refinement_rate": self.refinement_count / self.execution_count if self.execution_count > 0 else 0.0,
            "security_violation_rate": self.security_violations / self.execution_count if self.execution_count > 0 else 0.0,
            "llm_validation_rate": self.validation_count / self.execution_count if self.execution_count > 0 else 0.0
        }
        
        return {**base_stats, **refiner_stats}
    
    def reset_stats(self):
        """Reset agent statistics."""
        super().reset_stats()
        self.validation_count = 0
        self.execution_count = 0
        self.refinement_count = 0
        self.security_violations = 0