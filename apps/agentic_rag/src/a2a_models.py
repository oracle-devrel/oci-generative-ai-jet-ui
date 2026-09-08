"""
A2A Protocol Models and Data Structures

This module defines the Pydantic models for A2A (Agent2Agent) protocol communication,
including request/response models, agent cards, and task management structures.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Union
from enum import Enum
import uuid
from datetime import datetime


class TaskStatus(str, Enum):
    """Task status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class A2ARequest(BaseModel):
    """A2A JSON-RPC 2.0 request model"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name to call")
    params: Dict[str, Any] = Field(default_factory=dict, description="Method parameters")
    id: Union[str, int] = Field(default_factory=lambda: str(uuid.uuid4()), description="Request ID")


class A2AResponse(BaseModel):
    """A2A JSON-RPC 2.0 response model"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Method result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="Error information")
    id: Union[str, int] = Field(..., description="Request ID")


class A2AError(BaseModel):
    """A2A error model"""
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional error data")


class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str = Field(..., description="Capability name")
    description: str = Field(..., description="Capability description")
    input_schema: Dict[str, Any] = Field(..., description="Input parameter schema")
    output_schema: Optional[Dict[str, Any]] = Field(default=None, description="Output schema")


class AgentEndpoint(BaseModel):
    """Agent endpoint configuration"""
    base_url: str = Field(..., description="Base URL for the agent")
    authentication: Optional[Dict[str, Any]] = Field(default=None, description="Authentication requirements")


class AgentCard(BaseModel):
    """Agent card for discovery and capability advertisement"""
    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Human-readable agent name")
    version: str = Field(..., description="Agent version")
    description: str = Field(..., description="Agent description")
    capabilities: List[AgentCapability] = Field(..., description="List of agent capabilities")
    endpoints: AgentEndpoint = Field(..., description="Agent endpoint configuration")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class TaskInfo(BaseModel):
    """Task information model"""
    task_id: str = Field(..., description="Unique task identifier")
    task_type: str = Field(..., description="Type of task")
    status: TaskStatus = Field(..., description="Current task status")
    params: Dict[str, Any] = Field(..., description="Task parameters")
    result: Optional[Dict[str, Any]] = Field(default=None, description="Task result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    progress: Optional[float] = Field(default=None, description="Task progress (0.0 to 1.0)")


class DocumentQueryParams(BaseModel):
    """Parameters for document query capability"""
    query: str = Field(..., description="Query string")
    collection: Optional[str] = Field(default=None, description="Collection to search")
    use_cot: bool = Field(default=False, description="Use Chain of Thought reasoning")
    max_results: int = Field(default=3, description="Maximum number of results")


class DocumentUploadParams(BaseModel):
    """Parameters for document upload capability"""
    document_type: str = Field(..., description="Type of document (pdf, web, repository)")
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Document metadata")


class TaskCreateParams(BaseModel):
    """Parameters for task creation"""
    task_type: str = Field(..., description="Type of task to create")
    params: Dict[str, Any] = Field(..., description="Task-specific parameters")
    priority: Optional[int] = Field(default=0, description="Task priority")


class TaskStatusParams(BaseModel):
    """Parameters for task status check"""
    task_id: str = Field(..., description="Task ID to check")


class AgentDiscoverParams(BaseModel):
    """Parameters for agent discovery"""
    capability: Optional[str] = Field(default=None, description="Capability to search for")
    agent_id: Optional[str] = Field(default=None, description="Specific agent ID to find")
