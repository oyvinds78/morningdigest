import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import json

# Import agents with graceful fallback for missing dependencies
try:
    from ..agents.norwegian_news_agent import NorwegianNewsAgent
except ImportError as e:
    NorwegianNewsAgent = None
    print(f"Warning: NorwegianNewsAgent unavailable: {e}")

try:
    from ..agents.tech_intel_agent import TechIntelligenceAgent as TechIntelAgent
except ImportError as e:
    TechIntelAgent = None
    print(f"Warning: TechIntelAgent unavailable: {e}")

try:
    from ..agents.calendar_intelligence_agent import CalendarIntelligenceAgent
except ImportError as e:
    CalendarIntelligenceAgent = None
    print(f"Warning: CalendarIntelligenceAgent unavailable: {e}")

try:
    from ..agents.newsletter_intelligence_agent import NewsletterIntelligenceAgent
except ImportError as e:
    NewsletterIntelligenceAgent = None
    print(f"Warning: NewsletterIntelligenceAgent unavailable: {e}")

try:
    from ..agents.master_coordinator_agent import MasterCoordinatorAgent
except ImportError as e:
    MasterCoordinatorAgent = None
    print(f"Warning: MasterCoordinatorAgent unavailable: {e}")
from ..utils.error_handler import ErrorHandler, ErrorSeverity
from ..utils.token_counter import TokenCounter
from ..utils.config_loader import ConfigLoader


class AgentCoordinator:
    def __init__(self, config_loader: ConfigLoader, error_handler: ErrorHandler, token_counter: TokenCounter):
        self.config = config_loader
        self.error_handler = error_handler
        self.token_counter = token_counter
        self.logger = logging.getLogger('agent_coordinator')
        
        # Initialize agents
        self.agents = self._initialize_agents()
        
        # Agent processing order (respects dependencies)
        self.processing_order = [
            'norwegian_news',
            'tech_intelligence', 
            'calendar_intelligence',
            'newsletter_intelligence',
            'master_coordinator'
        ]

    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize all AI agents with error handling"""
        agents = {}
        api_key = self.config.get('claude.api_key')
        
        if not api_key:
            self.logger.error("Claude API key not found in configuration")
            return agents

        if NorwegianNewsAgent:
            try:
                agents['norwegian_news'] = NorwegianNewsAgent(api_key)
                self.logger.info("Norwegian News agent initialized")
            except Exception as e:
                self.error_handler.handle_error('agent_coordinator', e, ErrorSeverity.HIGH,
                                              {'agent': 'norwegian_news'})
                agents['norwegian_news'] = None
        else:
            agents['norwegian_news'] = None

        if TechIntelAgent:
            try:
                agents['tech_intelligence'] = TechIntelAgent(api_key)
                self.logger.info("Tech Intelligence agent initialized")
            except Exception as e:
                self.error_handler.handle_error('agent_coordinator', e, ErrorSeverity.HIGH,
                                              {'agent': 'tech_intelligence'})
                agents['tech_intelligence'] = None
        else:
            agents['tech_intelligence'] = None

        if CalendarIntelligenceAgent:
            try:
                agents['calendar_intelligence'] = CalendarIntelligenceAgent(api_key)
                self.logger.info("Calendar Intelligence agent initialized")
            except Exception as e:
                self.error_handler.handle_error('agent_coordinator', e, ErrorSeverity.HIGH,
                                              {'agent': 'calendar_intelligence'})
                agents['calendar_intelligence'] = None
        else:
            agents['calendar_intelligence'] = None

        if NewsletterIntelligenceAgent:
            try:
                agents['newsletter_intelligence'] = NewsletterIntelligenceAgent(api_key)
                self.logger.info("Newsletter Intelligence agent initialized")
            except Exception as e:
                self.error_handler.handle_error('agent_coordinator', e, ErrorSeverity.HIGH,
                                              {'agent': 'newsletter_intelligence'})
                agents['newsletter_intelligence'] = None
        else:
            agents['newsletter_intelligence'] = None

        if MasterCoordinatorAgent:
            try:
                agents['master_coordinator'] = MasterCoordinatorAgent(api_key)
                self.logger.info("Master Coordinator agent initialized")
            except Exception as e:
                self.error_handler.handle_error('agent_coordinator', e, ErrorSeverity.CRITICAL,
                                              {'agent': 'master_coordinator'})
                agents['master_coordinator'] = None
        else:
            agents['master_coordinator'] = None

        return agents

    async def process_all_data(self, raw_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process all collected data through specialized agents"""
        self.logger.info("Starting agent processing pipeline")
        
        agent_results = {}
        
        # Process specialized agents in parallel (they don't depend on each other)
        parallel_tasks = []
        
        if self.agents['norwegian_news'] and raw_data.get('news'):
            parallel_tasks.append(self._process_with_agent('norwegian_news', raw_data['news'], context))
        
        if self.agents['tech_intelligence'] and raw_data.get('medium'):
            parallel_tasks.append(self._process_with_agent('tech_intelligence', raw_data['medium'], context))
        
        if self.agents['calendar_intelligence'] and raw_data.get('calendar'):
            parallel_tasks.append(self._process_with_agent('calendar_intelligence', raw_data['calendar'], context))
        
        if self.agents['newsletter_intelligence'] and raw_data.get('gmail'):
            parallel_tasks.append(self._process_with_agent('newsletter_intelligence', raw_data['gmail'], context))

        # Execute parallel processing
        if parallel_tasks:
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
            
            # Collect results
            for result in parallel_results:
                if isinstance(result, dict) and 'agent' in result:
                    agent_results[result['agent']] = result['data']
                elif isinstance(result, Exception):
                    self.logger.error(f"Agent processing failed: {result}")

        self.logger.info(f"Agent processing completed. Processed: {list(agent_results.keys())}")
        return agent_results

    async def _process_with_agent(self, agent_name: str, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with a specific agent"""
        try:
            agent = self.agents[agent_name]
            if not agent:
                return {'agent': agent_name, 'data': None, 'error': 'Agent not initialized'}
            
            # Check token budget before processing
            estimated_tokens = self._estimate_tokens_for_agent(agent_name, data)
            can_proceed, budget_message = self.token_counter.check_budget(estimated_tokens)
            
            if not can_proceed:
                self.logger.warning(f"Skipping {agent_name} due to token budget: {budget_message}")
                return {
                    'agent': agent_name, 
                    'data': None, 
                    'error': f'Token budget exceeded: {budget_message}'
                }
            
            # Process with agent
            self.logger.info(f"Processing with {agent_name}")
            result = await agent.process(data, context)
            
            self.logger.info(f"Successfully processed with {agent_name}")
            return {'agent': agent_name, 'data': result, 'error': None}
            
        except Exception as e:
            self.error_handler.handle_async_error(
                'agent_coordinator', 
                e, 
                ErrorSeverity.HIGH,
                {'agent': agent_name, 'data_type': type(data).__name__}
            )
            return {'agent': agent_name, 'data': None, 'error': str(e)}

    def _estimate_tokens_for_agent(self, agent_name: str, data: Any) -> int:
        """Estimate token usage for agent processing"""
        # Base token estimates per agent type
        base_estimates = {
            'norwegian_news': 800,
            'tech_intelligence': 600, 
            'calendar_intelligence': 400,
            'newsletter_intelligence': 700,
            'master_coordinator': 1200
        }
        
        base_estimate = base_estimates.get(agent_name, 500)
        
        # Adjust based on data size
        if isinstance(data, dict):
            data_size_factor = len(str(data)) / 1000  # rough estimate
            return int(base_estimate + (data_size_factor * 100))
        elif isinstance(data, list):
            data_size_factor = len(data) / 10
            return int(base_estimate + (data_size_factor * 50))
        
        return base_estimate

    async def coordinate_final_digest(self, agent_results: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Use master coordinator to create final digest"""
        try:
            master_agent = self.agents['master_coordinator']
            if not master_agent:
                raise RuntimeError("Master coordinator agent not available")
            
            # Prepare input for master coordinator
            coordinator_input = {
                'agent_results': agent_results,
                'context': context,
                'processing_metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'successful_agents': [name for name, result in agent_results.items() if result and not result.get('error')],
                    'failed_agents': [name for name, result in agent_results.items() if not result or result.get('error')]
                }
            }
            
            # Check token budget for master coordinator
            estimated_tokens = self._estimate_tokens_for_agent('master_coordinator', coordinator_input)
            can_proceed, budget_message = self.token_counter.check_budget(estimated_tokens)
            
            if not can_proceed:
                self.logger.error(f"Cannot run master coordinator due to token budget: {budget_message}")
                return self._create_simple_digest_fallback(agent_results)
            
            self.logger.info("Running master coordinator for final digest")
            final_digest = await master_agent.process(coordinator_input, context)
            
            return final_digest
            
        except Exception as e:
            self.error_handler.handle_async_error(
                'agent_coordinator', 
                e, 
                ErrorSeverity.CRITICAL,
                {'agent_results_keys': list(agent_results.keys())}
            )
            # Return simple fallback digest
            return self._create_simple_digest_fallback(agent_results)

    def _create_simple_digest_fallback(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create simple digest when master coordinator fails"""
        digest = {
            'title': 'Morning Digest',
            'subtitle': 'Simplified digest (master coordinator unavailable)',
            'generated_at': datetime.now().isoformat(),
            'status': 'fallback_mode',
            'sections': []
        }
        
        # Priority order for sections
        section_order = [
            ('norwegian_news', 'Norwegian News', 'high'),
            ('calendar_intelligence', 'Today\'s Schedule', 'high'),  
            ('tech_intelligence', 'Technology Updates', 'medium'),
            ('newsletter_intelligence', 'Newsletter Insights', 'medium')
        ]
        
        for agent_key, section_title, priority in section_order:
            if agent_key in agent_results and agent_results[agent_key]:
                result = agent_results[agent_key]
                if result and not result.get('error'):
                    section = {
                        'title': section_title,
                        'priority': priority,
                        'content': result.get('summary', 'Analysis completed'),
                        'details': result.get('highlights', [])
                    }
                    digest['sections'].append(section)
        
        # Add summary
        successful_agents = [name for name, result in agent_results.items() if result and not result.get('error')]
        digest['processing_summary'] = {
            'successful_analyses': len(successful_agents),
            'total_agents': len(agent_results),
            'mode': 'simplified_fallback'
        }
        
        return digest

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all agents"""
        status = {
            'timestamp': datetime.now().isoformat(),
            'agents': {},
            'overall_status': 'healthy'
        }
        
        # Check each agent
        failed_agents = 0
        for name, agent in self.agents.items():
            if agent is None:
                status['agents'][name] = {
                    'status': 'not_initialized',
                    'last_check': datetime.now().isoformat()
                }
                failed_agents += 1
            else:
                # Try to perform a simple health check
                try:
                    # Simple test with minimal data
                    test_result = await self._test_agent_health(name, agent)
                    status['agents'][name] = {
                        'status': 'healthy' if test_result else 'unhealthy',
                        'last_check': datetime.now().isoformat()
                    }
                    if not test_result:
                        failed_agents += 1
                except Exception as e:
                    status['agents'][name] = {
                        'status': 'error',
                        'error': str(e),
                        'last_check': datetime.now().isoformat()
                    }
                    failed_agents += 1
        
        # Determine overall status
        total_agents = len(self.agents)
        if failed_agents == 0:
            status['overall_status'] = 'healthy'
        elif failed_agents < total_agents / 2:
            status['overall_status'] = 'degraded'
        else:
            status['overall_status'] = 'unhealthy'
        
        status['failed_agents'] = failed_agents
        status['total_agents'] = total_agents
        
        return status

    async def _test_agent_health(self, agent_name: str, agent: Any) -> bool:
        """Test agent health with minimal data"""
        try:
            # Create minimal test data
            test_data = {'test': True, 'health_check': True}
            test_context = {'test_mode': True}
            
            # Try processing with timeout
            result = await asyncio.wait_for(
                agent.process(test_data, test_context),
                timeout=10.0
            )
            
            # Check if result is valid
            return isinstance(result, dict) and not result.get('error')
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Health check timeout for {agent_name}")
            return False
        except Exception as e:
            self.logger.warning(f"Health check failed for {agent_name}: {e}")
            return False

    async def process_single_agent(self, agent_name: str, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process data with a single agent (for testing/debugging)"""
        if agent_name not in self.agents:
            return {'error': f'Unknown agent: {agent_name}', 'data': None}
        
        agent = self.agents[agent_name]
        if not agent:
            return {'error': f'Agent {agent_name} not initialized', 'data': None}
        
        return await self._process_with_agent(agent_name, data, context)

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about all available agents"""
        info = {
            'total_agents': len(self.agents),
            'initialized_agents': sum(1 for agent in self.agents.values() if agent is not None),
            'agents': {}
        }
        
        for name, agent in self.agents.items():
            info['agents'][name] = {
                'initialized': agent is not None,
                'class': agent.__class__.__name__ if agent else None
            }
        
        return info

    async def reset_agents(self):
        """Reset/reinitialize all agents"""
        self.logger.info("Resetting all agents")
        
        # Close existing agents if they have cleanup methods
        for name, agent in self.agents.items():
            if agent and hasattr(agent, 'cleanup'):
                try:
                    await agent.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error cleaning up {name}: {e}")
        
        # Reinitialize
        self.agents = self._initialize_agents()
        self.logger.info("All agents reset")