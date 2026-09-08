"""
Agent Registry for A2A Protocol

This module implements agent discovery and registry functionality,
allowing agents to register themselves and discover other agents.
"""

import logging
from typing import Dict, List, Optional, Any
from src.a2a_models import AgentCard

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing agent discovery and capabilities"""
    
    def __init__(self):
        """Initialize agent registry"""
        self.registered_agents: Dict[str, AgentCard] = {}
        self.capability_index: Dict[str, List[str]] = {}  # capability -> agent_ids
    
    def register_agent(self, agent_card: AgentCard) -> bool:
        """Register an agent with its capabilities"""
        try:
            agent_id = agent_card.agent_id
            
            # Store agent card
            self.registered_agents[agent_id] = agent_card
            
            # Update capability index
            for capability in agent_card.capabilities:
                cap_name = capability.name
                if cap_name not in self.capability_index:
                    self.capability_index[cap_name] = []
                
                if agent_id not in self.capability_index[cap_name]:
                    self.capability_index[cap_name].append(agent_id)
            
            logger.info(f"Registered agent {agent_id} with {len(agent_card.capabilities)} capabilities")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent: {str(e)}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        if agent_id not in self.registered_agents:
            return False
        
        agent_card = self.registered_agents[agent_id]
        
        # Remove from capability index
        for capability in agent_card.capabilities:
            cap_name = capability.name
            if cap_name in self.capability_index:
                if agent_id in self.capability_index[cap_name]:
                    self.capability_index[cap_name].remove(agent_id)
        
        # Remove agent
        del self.registered_agents[agent_id]
        
        logger.info(f"Unregistered agent {agent_id}")
        return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """Get agent by ID"""
        return self.registered_agents.get(agent_id)
    
    def discover_agents(self, capability: Optional[str] = None) -> List[AgentCard]:
        """Discover agents by capability"""
        if capability:
            # Find agents with specific capability
            agent_ids = self.capability_index.get(capability, [])
            return [self.registered_agents[aid] for aid in agent_ids if aid in self.registered_agents]
        else:
            # Return all agents
            return list(self.registered_agents.values())
    
    def search_agents(self, query: str) -> List[AgentCard]:
        """Search agents by name or description"""
        query_lower = query.lower()
        matching_agents = []
        
        for agent_card in self.registered_agents.values():
            if (query_lower in agent_card.name.lower() or 
                query_lower in agent_card.description.lower()):
                matching_agents.append(agent_card)
        
        return matching_agents
    
    def get_capabilities(self) -> List[str]:
        """Get all available capabilities"""
        return list(self.capability_index.keys())
    
    def get_agents_by_capability(self, capability: str) -> List[str]:
        """Get agent IDs that have a specific capability"""
        return self.capability_index.get(capability, [])
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents with basic info"""
        agents_info = []
        for agent_id, agent_card in self.registered_agents.items():
            agents_info.append({
                "agent_id": agent_id,
                "name": agent_card.name,
                "version": agent_card.version,
                "description": agent_card.description,
                "capabilities": [cap.name for cap in agent_card.capabilities],
                "endpoint": agent_card.endpoints.base_url
            })
        
        return agents_info
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            "total_agents": len(self.registered_agents),
            "total_capabilities": len(self.capability_index),
            "capabilities": list(self.capability_index.keys()),
            "agents": list(self.registered_agents.keys())
        }
