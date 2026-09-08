from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
import logging
import warnings
from transformers import logging as transformers_logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Suppress specific transformers warnings
transformers_logging.set_verbosity_error()
warnings.filterwarnings("ignore", message="Setting `pad_token_id` to `eos_token_id`")

class Agent(BaseModel):
    """Base agent class with common properties"""
    name: str
    role: str
    description: str
    llm: Any = Field(description="Language model for the agent")
    
    def log_prompt(self, prompt: str, prefix: str = ""):
        """Log a prompt being sent to the LLM"""
        # Check if the prompt contains context
        if "Context:" in prompt:
            # Split the prompt at "Context:" and keep only the first part
            parts = prompt.split("Context:")
            # Keep the first part and add a note that context is omitted
            truncated_prompt = parts[0] + "Context: [Context omitted for brevity]"
            if len(parts) > 2 and "Key Findings:" in parts[1]:
                # For researcher prompts, keep the "Key Findings:" part
                key_findings_part = parts[1].split("Key Findings:")
                if len(key_findings_part) > 1:
                    truncated_prompt += "\nKey Findings:" + key_findings_part[1]
            logger.info(f"\n{'='*80}\n{prefix} Prompt:\n{'-'*40}\n{truncated_prompt}\n{'='*80}")
        else:
            # If no context, log the full prompt
            logger.info(f"\n{'='*80}\n{prefix} Prompt:\n{'-'*40}\n{prompt}\n{'='*80}")
        
    def log_response(self, response: str, prefix: str = ""):
        """Log a response received from the LLM"""
        # Log the response but truncate if it's too long
        if len(response) > 500:
            truncated_response = response[:500] + "... [response truncated]"
            logger.info(f"\n{'='*80}\n{prefix} Response:\n{'-'*40}\n{truncated_response}\n{'='*80}")
        else:
            logger.info(f"\n{'='*80}\n{prefix} Response:\n{'-'*40}\n{response}\n{'='*80}")

class PlannerAgent(Agent):
    """Agent responsible for breaking down problems and planning steps"""
    def __init__(self, llm):
        super().__init__(
            name="Planner",
            role="Strategic Planner",
            description="Breaks down complex problems into manageable steps",
            llm=llm
        )
        
    def plan(self, query: str, context: List[Dict[str, Any]] = None) -> str:
        logger.info(f"\n🎯 Planning step for query: {query}")
        
        if context:
            template = """As a strategic planner, break down this problem into 3-4 clear steps.
            
            Context: {context}
            Query: {query}
            
            Steps:"""
            context_str = "\n\n".join([f"Context {i+1}:\n{item['content']}" for i, item in enumerate(context)])
            logger.info(f"Using context ({len(context)} items)")
        else:
            template = """As a strategic planner, break down this problem into 3-4 clear steps.
            
            Query: {query}
            
            Steps:"""
            context_str = ""
            logger.info("No context available")
            
        prompt = ChatPromptTemplate.from_template(template)
        messages = prompt.format_messages(query=query, context=context_str)
        prompt_text = "\n".join([msg.content for msg in messages])
        self.log_prompt(prompt_text, "Planner")
        
        response = self.llm.invoke(messages)
        self.log_response(response.content, "Planner")
        return response.content

class ResearchAgent(Agent):
    """Agent responsible for gathering and analyzing information"""
    vector_store: Any = Field(description="Vector store for searching")
    
    def __init__(self, llm, vector_store):
        super().__init__(
            name="Researcher",
            role="Information Gatherer",
            description="Gathers and analyzes relevant information from knowledge bases",
            llm=llm,
            vector_store=vector_store
        )
        
    def research(self, query: str, step: str) -> List[Dict[str, Any]]:
        logger.info(f"\n🔍 Researching for step: {step}")
        
        # Query all collections
        pdf_results = self.vector_store.query_pdf_collection(query)
        repo_results = self.vector_store.query_repo_collection(query)
        
        # Combine results
        all_results = pdf_results + repo_results
        logger.info(f"Found {len(all_results)} relevant documents")
        
        if not all_results:
            logger.warning("No relevant documents found")
            return []
            
        template = """Extract and summarize key information relevant to this step.
        
        Step: {step}
        Context: {context}
        
        Key Findings:"""
        
        # Create context string but don't log it
        context_str = "\n\n".join([f"Source {i+1}:\n{item['content']}" for i, item in enumerate(all_results)])
        prompt = ChatPromptTemplate.from_template(template)
        messages = prompt.format_messages(step=step, context=context_str)
        prompt_text = "\n".join([msg.content for msg in messages])
        self.log_prompt(prompt_text, "Researcher")
        
        response = self.llm.invoke(messages)
        self.log_response(response.content, "Researcher")
        
        return [{"content": response.content, "metadata": {"source": "Research Summary"}}]

class ReasoningAgent(Agent):
    """Agent responsible for logical reasoning and analysis"""
    def __init__(self, llm):
        super().__init__(
            name="Reasoner",
            role="Logic and Analysis",
            description="Applies logical reasoning to information and draws conclusions",
            llm=llm
        )
        
    def reason(self, query: str, step: str, context: List[Dict[str, Any]]) -> str:
        logger.info(f"\n🤔 Reasoning about step: {step}")
        
        template = """Analyze the information and draw a clear conclusion for this step.
        
        Step: {step}
        Context: {context}
        Query: {query}
        
        Conclusion:"""
        
        # Create context string but don't log it
        context_str = "\n\n".join([f"Context {i+1}:\n{item['content']}" for i, item in enumerate(context)])
        prompt = ChatPromptTemplate.from_template(template)
        messages = prompt.format_messages(step=step, query=query, context=context_str)
        prompt_text = "\n".join([msg.content for msg in messages])
        self.log_prompt(prompt_text, "Reasoner")
        
        response = self.llm.invoke(messages)
        self.log_response(response.content, "Reasoner")
        return response.content

class SynthesisAgent(Agent):
    """Agent responsible for combining information and generating final response"""
    def __init__(self, llm):
        super().__init__(
            name="Synthesizer",
            role="Information Synthesizer",
            description="Combines multiple pieces of information into a coherent response",
            llm=llm
        )
        
    def synthesize(self, query: str, reasoning_steps: List[str]) -> str:
        logger.info(f"\n📝 Synthesizing final answer from {len(reasoning_steps)} reasoning steps")
        
        template = """Combine the reasoning steps into a clear, comprehensive answer.
        
        Query: {query}
        Steps: {steps}
        
        Answer:"""
        
        steps_str = "\n\n".join([f"Step {i+1}:\n{step}" for i, step in enumerate(reasoning_steps)])
        prompt = ChatPromptTemplate.from_template(template)
        messages = prompt.format_messages(query=query, steps=steps_str)
        prompt_text = "\n".join([msg.content for msg in messages])
        self.log_prompt(prompt_text, "Synthesizer")
        
        response = self.llm.invoke(messages)
        self.log_response(response.content, "Synthesizer")
        return response.content

def create_agents(llm, vector_store=None):
    """Create and return the set of specialized agents"""
    return {
        "planner": PlannerAgent(llm),
        "researcher": ResearchAgent(llm, vector_store) if vector_store else None,
        "reasoner": ReasoningAgent(llm),
        "synthesizer": SynthesisAgent(llm)
    } 