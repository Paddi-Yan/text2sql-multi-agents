"""
LLM Service for handling language model API calls.
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import openai
from openai import OpenAI

from config.settings import config


@dataclass
class LLMResponse:
    """LLM response wrapper."""
    content: str
    success: bool
    error: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


class LLMService:
    """Service for interacting with Language Models."""
    
    def __init__(self, model_name: Optional[str] = None, api_key: Optional[str] = None, 
                 base_url: Optional[str] = None):
        """Initialize LLM service.
        
        Args:
            model_name: Model name to use
            api_key: API key for authentication
            base_url: Base URL for API calls
        """
        self.model_name = model_name or os.getenv("OPENAI_MODEL_NAME", "gpt-4")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")
        
        # Initialize OpenAI client
        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
            
        self.client = OpenAI(**client_kwargs)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Initialized LLM service with model: {self.model_name}")
    
    def generate_completion(self, prompt: str, temperature: float = 0.1, 
                          max_tokens: int = 2000, system_prompt: Optional[str] = None) -> LLMResponse:
        """Generate completion from LLM.
        
        Args:
            prompt: User prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            
        Returns:
            LLMResponse with generated content
        """
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            self.logger.debug(f"Calling LLM with {len(messages)} messages")
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=30
            )
            
            content = response.choices[0].message.content
            usage = response.usage.model_dump() if response.usage else None
            
            self.logger.debug(f"LLM response received: {len(content)} characters")
            
            return LLMResponse(
                content=content,
                success=True,
                usage=usage,
                model=self.model_name
            )
            
        except Exception as e:
            self.logger.error(f"LLM API call failed: {e}")
            return LLMResponse(
                content="",
                success=False,
                error=str(e)
            )
    
    def decompose_query(self, query: str, schema_info: str, evidence: str = "", 
                       complexity_info: Optional[Dict] = None) -> LLMResponse:
        """Decompose a complex query into sub-questions.
        
        Args:
            query: Natural language query
            schema_info: Database schema information
            evidence: Additional evidence or context
            complexity_info: Query complexity analysis
            
        Returns:
            LLMResponse with decomposed sub-questions
        """
        system_prompt = """You are an expert at analyzing natural language database queries and breaking them down into logical sub-steps.

Your task is to decompose complex queries into simpler sub-questions that can be answered step by step. Each sub-question should be clear, specific, and answerable with a single SQL query.

Guidelines:
1. Break the question into logical sub-steps
2. Each sub-question should be answerable with a single SQL query
3. Maintain the logical flow from simple to complex
4. Ensure all sub-questions contribute to answering the original question
5. For simple queries, you may return just the original question

Output format:
Return a JSON object with the following structure:
{
    "sub_questions": [
        "Sub-question 1",
        "Sub-question 2",
        ...
    ],
    "reasoning": "Brief explanation of the decomposition approach"
}"""

        prompt_parts = [
            f"**Original Question:** {query}",
            "",
            "**Database Schema:**",
            schema_info,
            ""
        ]
        
        if evidence:
            prompt_parts.extend([
                "**Additional Evidence:**",
                evidence,
                ""
            ])
        
        if complexity_info:
            prompt_parts.extend([
                "**Complexity Analysis:**",
                f"Complexity score: {complexity_info.get('score', 0)}/8",
                "Detected patterns:"
            ])
            
            for indicator, present in complexity_info.get("indicators", {}).items():
                if present:
                    prompt_parts.append(f"- {indicator.replace('_', ' ').title()}")
            
            prompt_parts.append("")
        
        prompt_parts.extend([
            "Please decompose this query into sub-questions following the guidelines above.",
            "Return your response as a valid JSON object."
        ])
        
        prompt = "\n".join(prompt_parts)
        
        return self.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1000
        )
    
    def generate_sql(self, query: str, sub_questions: List[str], schema_info: str, 
                    fk_info: str = "", context: Optional[Dict[str, List]] = None,
                    use_cot: bool = True) -> LLMResponse:
        """Generate SQL query from natural language.
        
        Args:
            query: Original natural language query
            sub_questions: List of sub-questions (for CoT)
            schema_info: Database schema information
            fk_info: Foreign key relationships
            context: RAG context information
            use_cot: Whether to use Chain of Thought approach
            
        Returns:
            LLMResponse with generated SQL
        """
        if use_cot and len(sub_questions) > 1:
            return self._generate_cot_sql(query, sub_questions, schema_info, fk_info, context)
        else:
            return self._generate_simple_sql(query, schema_info, fk_info, context)
    
    def _generate_simple_sql(self, query: str, schema_info: str, fk_info: str = "",
                           context: Optional[Dict[str, List]] = None) -> LLMResponse:
        """Generate simple SQL query."""
        system_prompt = """You are an expert SQL developer. Generate accurate, efficient SQL queries based on natural language questions and database schema information.

Requirements:
1. Generate syntactically correct SQL
2. Use appropriate table and column names from the schema
3. Follow SQL best practices
4. Ensure the query logic matches the natural language question
5. Return only the SQL query without explanations

Output format: Return only the SQL query, nothing else."""

        prompt_parts = [
            f"**Question:** {query}",
            "",
            "**Database Schema:**",
            schema_info,
            ""
        ]
        
        if fk_info:
            prompt_parts.extend([
                "**Foreign Key Relationships:**",
                fk_info,
                ""
            ])
        
        # Add RAG context if available
        if context:
            if context.get("sql_examples"):
                prompt_parts.extend([
                    "**Similar SQL Examples:**",
                    ""
                ])
                for i, sql in enumerate(context["sql_examples"][:2], 1):
                    prompt_parts.extend([
                        f"Example {i}:",
                        f"```sql",
                        sql.strip(),
                        f"```",
                        ""
                    ])
            
            if context.get("qa_pairs"):
                high_quality_pairs = [p for p in context["qa_pairs"] if p.get("score", 0) >= 0.8][:2]
                if high_quality_pairs:
                    prompt_parts.extend([
                        "**Similar Question-SQL Pairs:**",
                        ""
                    ])
                    for i, pair in enumerate(high_quality_pairs, 1):
                        prompt_parts.extend([
                            f"Q{i}: {pair['question']}",
                            f"A{i}:",
                            f"```sql",
                            pair['sql'].strip(),
                            f"```",
                            ""
                        ])
        
        prompt_parts.append("Generate the SQL query:")
        prompt = "\n".join(prompt_parts)
        
        return self.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=1500
        )
    
    def _generate_cot_sql(self, query: str, sub_questions: List[str], schema_info: str,
                         fk_info: str = "", context: Optional[Dict[str, List]] = None) -> LLMResponse:
        """Generate SQL using Chain of Thought approach."""
        system_prompt = """You are an expert SQL developer using Chain of Thought reasoning. Generate SQL by solving sub-questions step by step, then combining them into a final query.

Process:
1. Address each sub-question with appropriate SQL logic
2. Build the final query by integrating the sub-solutions
3. Ensure the final SQL is syntactically correct and efficient

Output format: Return only the final SQL query, nothing else."""

        prompt_parts = [
            f"**Original Question:** {query}",
            "",
            "**Sub-questions to solve:**"
        ]
        
        for i, sub_q in enumerate(sub_questions, 1):
            prompt_parts.append(f"{i}. {sub_q}")
        
        prompt_parts.extend([
            "",
            "**Database Schema:**",
            schema_info,
            ""
        ])
        
        if fk_info:
            prompt_parts.extend([
                "**Foreign Key Relationships:**",
                fk_info,
                ""
            ])
        
        # Add context if available
        if context and context.get("sql_examples"):
            prompt_parts.extend([
                "**Reference SQL Patterns:**",
                ""
            ])
            for i, sql in enumerate(context["sql_examples"][:2], 1):
                prompt_parts.extend([
                    f"Pattern {i}:",
                    f"```sql",
                    sql.strip(),
                    f"```",
                    ""
                ])
        
        prompt_parts.extend([
            "Using Chain of Thought reasoning, generate a SQL query that addresses all sub-questions and answers the original question:",
            ""
        ])
        
        prompt = "\n".join(prompt_parts)
        
        return self.generate_completion(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=2000
        )
    
    def extract_json_from_response(self, response_content: str) -> Optional[Dict]:
        """Extract JSON object from LLM response.
        
        Args:
            response_content: Raw response content
            
        Returns:
            Parsed JSON object or None if parsing fails
        """
        try:
            # Try to find JSON in the response
            start_idx = response_content.find('{')
            end_idx = response_content.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response_content[start_idx:end_idx]
                return json.loads(json_str)
            
            # If no JSON found, try parsing the entire response
            return json.loads(response_content)
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON from LLM response: {e}")
            return None
    
    def extract_sql_from_response(self, response_content: str) -> str:
        """Extract SQL query from LLM response.
        
        Args:
            response_content: Raw response content
            
        Returns:
            Cleaned SQL query
        """
        # Remove markdown code blocks
        content = response_content.strip()
        
        # Remove ```sql and ``` markers
        if content.startswith('```sql'):
            content = content[6:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        # Clean up the SQL
        content = content.strip()
        
        # Remove any leading/trailing explanations
        lines = content.split('\n')
        sql_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('--') and not line.startswith('#'):
                sql_lines.append(line)
        
        return ' '.join(sql_lines) if sql_lines else content


# Global LLM service instance
llm_service = LLMService()