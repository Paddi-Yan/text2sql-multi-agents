"""
Centralized prompt templates for Text2SQL multi-agent system.
All prompts are organized by agent and functionality.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Template for LLM prompts."""
    system_prompt: str
    user_prompt_template: str
    description: str
    parameters: List[str]


class PromptManager:
    """Centralized prompt management for all agents."""
    
    def __init__(self):
        self.prompts = self._initialize_prompts()
    
    def _initialize_prompts(self) -> Dict[str, Dict[str, PromptTemplate]]:
        """Initialize all prompt templates."""
        return {
            "selector": self._get_selector_prompts(),
            "decomposer": self._get_decomposer_prompts(),
            "refiner": self._get_refiner_prompts(),
            "common": self._get_common_prompts()
        }
    
    def get_prompt(self, agent: str, prompt_type: str) -> PromptTemplate:
        """Get a specific prompt template."""
        if agent not in self.prompts:
            raise ValueError(f"Unknown agent: {agent}")
        if prompt_type not in self.prompts[agent]:
            raise ValueError(f"Unknown prompt type '{prompt_type}' for agent '{agent}'")
        return self.prompts[agent][prompt_type]
    
    def format_prompt(self, agent: str, prompt_type: str, **kwargs) -> tuple[str, str]:
        """Format a prompt with given parameters."""
        template = self.get_prompt(agent, prompt_type)
        
        # Check if all required parameters are provided
        missing_params = [param for param in template.parameters if param not in kwargs]
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")
        
        # Format the user prompt
        user_prompt = template.user_prompt_template.format(**kwargs)
        
        return template.system_prompt, user_prompt
    
    def _get_selector_prompts(self) -> Dict[str, PromptTemplate]:
        """Get all Selector agent prompts."""
        return {
            "schema_analysis": PromptTemplate(
                system_prompt="""You are an expert database schema analyzer. Your task is to analyze database schemas and determine if they need pruning based on complexity.

You should evaluate:
1. Total number of tables and columns
2. Average columns per table
3. Complexity of relationships
4. Token count estimation

Provide structured analysis with clear recommendations.""",
                
                user_prompt_template="""**Database Schema Analysis Task**

Please analyze the following database schema and determine if it needs pruning for query processing:

**Database ID:** {db_id}

**Schema Information:**
{schema_info}

**Statistics:**
- Total tables: {table_count}
- Total columns: {total_columns}
- Average columns per table: {avg_columns}

**Analysis Requirements:**
1. Evaluate schema complexity
2. Estimate token usage
3. Recommend pruning strategy
4. Identify key tables and relationships

**Output Format:**
Return a JSON object with the following structure:
{{
    "needs_pruning": boolean,
    "complexity_score": number (1-10),
    "token_estimate": number,
    "pruning_strategy": "string",
    "key_tables": ["table1", "table2"],
    "reasoning": "explanation of analysis"
}}""",
                
                description="Analyze database schema complexity and determine pruning needs",
                parameters=["db_id", "schema_info", "table_count", "total_columns", "avg_columns"]
            ),
            
            "schema_pruning": PromptTemplate(
                system_prompt="""You are an expert at database schema pruning for query optimization. Your task is to intelligently select relevant tables and columns based on a natural language query.

Guidelines:
1. Keep tables and columns that are directly relevant to the query
2. Preserve foreign key relationships for joins
3. Include ID columns for proper relationships
4. Remove irrelevant tables completely
5. For large tables, select only the most relevant columns

Output should be a structured decision for each table.""",
                
                user_prompt_template="""**Schema Pruning Task**

Based on the following natural language query, determine which tables and columns to keep from the database schema:

**Query:** {query}

**Database Schema:**
{schema_info}

**Foreign Key Relationships:**
{fk_info}

**Additional Context:**
{evidence}

**Pruning Instructions:**
For each table, decide:
- "keep_all": Keep the entire table
- "drop_all": Remove the table completely  
- ["col1", "col2", ...]: Keep only specified columns

**Output Format:**
Return a JSON object with the following structure:
{{
    "pruning_decisions": {{
        "table_name1": "keep_all" | "drop_all" | ["column1", "column2"],
        "table_name2": "keep_all" | "drop_all" | ["column1", "column2"]
    }},
    "reasoning": "explanation of pruning decisions",
    "preserved_relationships": ["relationship descriptions"]
}}""",
                
                description="Prune database schema based on query relevance",
                parameters=["query", "schema_info", "fk_info", "evidence"]
            )
        }
    
    def _get_decomposer_prompts(self) -> Dict[str, PromptTemplate]:
        """Get all Decomposer agent prompts."""
        return {
            "query_decomposition": PromptTemplate(
                system_prompt="""You are an expert at analyzing natural language database queries and breaking them down into logical sub-steps.

Your task is to decompose complex queries into simpler sub-questions that can be answered step by step. Each sub-question should be clear, specific, and answerable with a single SQL query.

Guidelines:
1. Break the question into logical sub-steps
2. Each sub-question should be answerable with a single SQL query
3. Maintain the logical flow from simple to complex
4. Ensure all sub-questions contribute to answering the original question
5. For simple queries, you may return just the original question

Consider the database schema and any additional context provided.""",
                
                user_prompt_template="""**Query Decomposition Task**

**Original Question:** {query}

**Database Schema:**
{schema_info}

{evidence_section}

{complexity_section}

Please decompose this query into sub-questions following the guidelines above.

**Output Format:**
Return a JSON object with the following structure:
{{
    "sub_questions": [
        "Sub-question 1",
        "Sub-question 2",
        ...
    ],
    "reasoning": "Brief explanation of the decomposition approach",
    "complexity_level": "simple" | "medium" | "complex"
}}""",
                
                description="Decompose complex queries into manageable sub-questions",
                parameters=["query", "schema_info", "evidence_section", "complexity_section"]
            ),
            
            "simple_sql_generation": PromptTemplate(
                system_prompt="""You are an expert SQL developer. Generate accurate, efficient SQL queries based on natural language questions and database schema information.

Requirements:
1. Generate syntactically correct SQL
2. Use appropriate table and column names from the schema
3. Follow SQL best practices
4. Ensure the query logic matches the natural language question
5. Return only the SQL query without explanations

Consider any provided examples and context to improve accuracy.""",
                
                user_prompt_template="""**SQL Generation Task**

**Question:** {query}

**Database Schema:**
{schema_info}

{fk_section}

{context_section}

Generate a SQL query that answers the question accurately.

**Requirements:**
- Use correct table and column names from the schema
- Follow SQL best practices and conventions
- Ensure syntactic correctness
- Match the query logic to the natural language question

**Output:** Return only the SQL query, nothing else.""",
                
                description="Generate simple SQL queries from natural language",
                parameters=["query", "schema_info", "fk_section", "context_section"]
            ),
            
            "cot_sql_generation": PromptTemplate(
                system_prompt="""You are an expert SQL developer using Chain of Thought reasoning. Generate SQL by solving sub-questions step by step, then combining them into a final query.

Process:
1. Address each sub-question with appropriate SQL logic
2. Build the final query by integrating the sub-solutions
3. Ensure the final SQL is syntactically correct and efficient
4. Use CTEs, subqueries, or joins as appropriate

Consider the database schema and relationships carefully.""",
                
                user_prompt_template="""**Chain of Thought SQL Generation**

**Original Question:** {original_query}

**Sub-questions to solve:**
{sub_questions_list}

**Database Schema:**
{schema_info}

{fk_section}

{context_section}

Using Chain of Thought reasoning, generate a SQL query that addresses all sub-questions and answers the original question.

**Approach:**
1. Consider how each sub-question contributes to the solution
2. Plan the query structure (CTEs, joins, aggregations)
3. Build the final integrated query

**Output:** Return only the final SQL query, nothing else.""",
                
                description="Generate complex SQL using Chain of Thought reasoning",
                parameters=["original_query", "sub_questions_list", "schema_info", "fk_section", "context_section"]
            )
        }
    
    def _get_refiner_prompts(self) -> Dict[str, PromptTemplate]:
        """Get all Refiner agent prompts."""
        return {
            "sql_validation": PromptTemplate(
                system_prompt="""You are an expert SQL validator and debugger. Your task is to analyze SQL queries for syntax errors, logical issues, and potential improvements.

Focus on:
1. Syntax correctness
2. Logical consistency
3. Performance considerations
4. Security issues
5. Best practices compliance""",
                
                user_prompt_template="""**SQL Validation Task**

**SQL Query to Validate:**
```sql
{sql_query}
```

**Database Schema:**
{schema_info}

**Original Question:** {original_query}

**Validation Requirements:**
1. Check syntax correctness
2. Verify table and column names exist
3. Validate join conditions
4. Check for logical consistency
5. Identify potential security issues

**Output Format:**
Return a JSON object with the following structure:
{{
    "is_valid": boolean,
    "syntax_errors": ["error1", "error2"],
    "logical_issues": ["issue1", "issue2"],
    "security_concerns": ["concern1", "concern2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "corrected_sql": "corrected SQL if needed"
}}""",
                
                description="Validate and analyze SQL queries for errors and improvements",
                parameters=["sql_query", "schema_info", "original_query"]
            ),
            
            "sql_refinement": PromptTemplate(
                system_prompt="""You are an expert SQL developer specializing in query refinement and error correction. Your task is to fix SQL queries based on execution errors and feedback.

Guidelines:
1. Analyze the error message carefully
2. Identify the root cause of the issue
3. Apply appropriate fixes
4. Ensure the corrected query maintains the original intent
5. Optimize for performance when possible""",
                
                user_prompt_template="""**SQL Refinement Task**

**Original SQL Query:**
```sql
{original_sql}
```

**Error Information:**
{error_info}

**Database Schema:**
{schema_info}

**Original Question:** {original_query}

**Context:** {context}

Based on the error information, please provide a corrected SQL query that:
1. Fixes the identified issues
2. Maintains the original query intent
3. Uses correct syntax and table/column names
4. Follows SQL best practices

**Output:** Return only the corrected SQL query, nothing else.""",
                
                description="Refine and correct SQL queries based on errors",
                parameters=["original_sql", "error_info", "schema_info", "original_query", "context"]
            )
        }
    
    def _get_common_prompts(self) -> Dict[str, PromptTemplate]:
        """Get common prompts used across agents."""
        return {
            "context_builder": PromptTemplate(
                system_prompt="""You are a context builder for Text2SQL systems. Build relevant context sections for prompts.""",
                
                user_prompt_template="""Build context sections for the following data:

**Foreign Key Information:**
{fk_info}

**RAG Context:**
{rag_context}

Format as appropriate sections for inclusion in other prompts.""",
                
                description="Build context sections for other prompts",
                parameters=["fk_info", "rag_context"]
            )
        }


# Global prompt manager instance
prompt_manager = PromptManager()


# Convenience functions for common operations
def get_selector_schema_analysis_prompt(db_id: str, schema_info: str, table_count: int, 
                                      total_columns: int, avg_columns: float) -> tuple[str, str]:
    """Get formatted schema analysis prompt for Selector agent."""
    return prompt_manager.format_prompt(
        "selector", "schema_analysis",
        db_id=db_id,
        schema_info=schema_info,
        table_count=table_count,
        total_columns=total_columns,
        avg_columns=avg_columns
    )


def get_selector_pruning_prompt(query: str, schema_info: str, fk_info: str, evidence: str) -> tuple[str, str]:
    """Get formatted schema pruning prompt for Selector agent."""
    return prompt_manager.format_prompt(
        "selector", "schema_pruning",
        query=query,
        schema_info=schema_info,
        fk_info=fk_info,
        evidence=evidence
    )


def get_decomposer_query_decomposition_prompt(query: str, schema_info: str, 
                                            evidence: str = "", complexity_info: Optional[Dict] = None) -> tuple[str, str]:
    """Get formatted query decomposition prompt for Decomposer agent."""
    evidence_section = f"""**Additional Evidence:**
{evidence}
""" if evidence else ""
    
    complexity_section = ""
    if complexity_info:
        complexity_section = f"""**Complexity Analysis:**
Complexity score: {complexity_info.get('score', 0)}/8
Detected patterns:"""
        
        for indicator, present in complexity_info.get("indicators", {}).items():
            if present:
                complexity_section += f"\n- {indicator.replace('_', ' ').title()}"
        
        complexity_section += "\n"
    
    return prompt_manager.format_prompt(
        "decomposer", "query_decomposition",
        query=query,
        schema_info=schema_info,
        evidence_section=evidence_section,
        complexity_section=complexity_section
    )


def get_decomposer_simple_sql_prompt(query: str, schema_info: str, fk_info: str = "", 
                                   context: Optional[Dict[str, List]] = None) -> tuple[str, str]:
    """Get formatted simple SQL generation prompt for Decomposer agent."""
    fk_section = f"""**Foreign Key Relationships:**
{fk_info}
""" if fk_info else ""
    
    context_section = _build_context_section(context)
    
    return prompt_manager.format_prompt(
        "decomposer", "simple_sql_generation",
        query=query,
        schema_info=schema_info,
        fk_section=fk_section,
        context_section=context_section
    )


def get_decomposer_cot_sql_prompt(original_query: str, sub_questions: List[str], 
                                schema_info: str, fk_info: str = "", 
                                context: Optional[Dict[str, List]] = None) -> tuple[str, str]:
    """Get formatted CoT SQL generation prompt for Decomposer agent."""
    sub_questions_list = "\n".join(f"{i}. {sq}" for i, sq in enumerate(sub_questions, 1))
    
    fk_section = f"""**Foreign Key Relationships:**
{fk_info}
""" if fk_info else ""
    
    context_section = _build_context_section(context)
    
    return prompt_manager.format_prompt(
        "decomposer", "cot_sql_generation",
        original_query=original_query,
        sub_questions_list=sub_questions_list,
        schema_info=schema_info,
        fk_section=fk_section,
        context_section=context_section
    )


def get_refiner_validation_prompt(sql_query: str, schema_info: str, original_query: str) -> tuple[str, str]:
    """Get formatted SQL validation prompt for Refiner agent."""
    return prompt_manager.format_prompt(
        "refiner", "sql_validation",
        sql_query=sql_query,
        schema_info=schema_info,
        original_query=original_query
    )


def get_refiner_refinement_prompt(original_sql: str, error_info: str, schema_info: str, 
                                original_query: str, context: str = "") -> tuple[str, str]:
    """Get formatted SQL refinement prompt for Refiner agent."""
    return prompt_manager.format_prompt(
        "refiner", "sql_refinement",
        original_sql=original_sql,
        error_info=error_info,
        schema_info=schema_info,
        original_query=original_query,
        context=context
    )


def _build_context_section(context: Optional[Dict[str, List]]) -> str:
    """Build context section from RAG context data."""
    if not context:
        return ""
    
    sections = []
    
    # Add SQL examples
    if context.get("sql_examples"):
        sections.append("**Similar SQL Examples:**")
        sections.append("The following examples show similar query patterns:")
        sections.append("")
        for i, sql in enumerate(context["sql_examples"][:2], 1):
            sections.extend([
                f"Example {i}:",
                f"```sql",
                sql.strip(),
                f"```",
                ""
            ])
    
    # Add high-quality QA pairs
    if context.get("qa_pairs"):
        high_quality_pairs = [p for p in context["qa_pairs"] if p.get("score", 0) >= 0.8][:2]
        if high_quality_pairs:
            sections.append("**Similar Question-SQL Pairs:**")
            sections.append("")
            for i, pair in enumerate(high_quality_pairs, 1):
                sections.extend([
                    f"Q{i}: {pair['question']}",
                    f"A{i}:",
                    f"```sql",
                    pair['sql'].strip(),
                    f"```",
                    ""
                ])
    
    # Add documentation context
    if context.get("documentation"):
        sections.append("**Business Context:**")
        sections.append("The following documentation provides business context:")
        sections.append("")
        for i, doc in enumerate(context["documentation"][:2], 1):
            sections.extend([
                f"Context {i}:",
                doc.strip(),
                ""
            ])
    
    return "\n".join(sections) if sections else ""