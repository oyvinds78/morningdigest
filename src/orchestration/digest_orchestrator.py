import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import collectors and agents with graceful fallback for missing dependencies
try:
    from ..collectors.news_collector import NewsCollector
except ImportError as e:
    NewsCollector = None
    print(f"Warning: NewsCollector unavailable: {e}")

try:
    from ..collectors.calendar_collector import CalendarCollector
except ImportError as e:
    CalendarCollector = None
    print(f"Warning: CalendarCollector unavailable: {e}")

try:
    from ..collectors.gmail_collector import GmailCollector
except ImportError as e:
    GmailCollector = None
    print(f"Warning: GmailCollector unavailable: {e}")

try:
    from ..collectors.medium_collector import MediumCollector
except ImportError as e:
    MediumCollector = None
    print(f"Warning: MediumCollector unavailable: {e}")

try:
    from ..collectors.weather_collector import WeatherCollector
except ImportError as e:
    WeatherCollector = None
    print(f"Warning: WeatherCollector unavailable: {e}")

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
from .agent_coordinator import AgentCoordinator


class DigestOrchestrator:
    def __init__(self, config_loader: ConfigLoader, error_handler: ErrorHandler, token_counter: TokenCounter):
        self.config = config_loader
        self.error_handler = error_handler
        self.token_counter = token_counter
        self.logger = logging.getLogger('digest_orchestrator')
        
        # Initialize collectors
        self.collectors = self._initialize_collectors()
        
        # Initialize agent coordinator
        self.agent_coordinator = AgentCoordinator(
            config_loader=config_loader,
            error_handler=error_handler,
            token_counter=token_counter
        )
        
        # Norwegian context
        self.context = {
            'location': 'Trondheim, Norway',
            'family_context': 'Parent with boys aged 5 and 7',
            'career_focus': 'Restaurant experience transitioning to ML engineer, aged 47',
            'interests': [
                'learning', 'efficiency', 'AI', 'ML', 'critical thinking', 
                'Premier League', 'Eliteserien fotball', 'family', 
                'environment', 'science', 'music', 'writing'
            ],
            'language_preference': 'Norwegian and English',
            'timezone': 'Europe/Oslo'
        }

    def _initialize_collectors(self) -> Dict[str, Any]:
        """Initialize all data collectors with error handling"""
        collectors = {}
        
        if NewsCollector:
            try:
                collectors['news'] = NewsCollector()
                self.logger.info("News collector initialized")
            except Exception as e:
                self.error_handler.handle_error('digest_orchestrator', e, ErrorSeverity.MEDIUM, 
                                              {'collector': 'news'})
                collectors['news'] = None
        else:
            collectors['news'] = None

        if CalendarCollector:
            try:
                collectors['calendar'] = CalendarCollector(self.config)
                self.logger.info("Calendar collector initialized")
            except Exception as e:
                self.error_handler.handle_error('digest_orchestrator', e, ErrorSeverity.MEDIUM,
                                              {'collector': 'calendar'})
                collectors['calendar'] = None
        else:
            collectors['calendar'] = None

        if GmailCollector:
            try:
                collectors['gmail'] = GmailCollector(self.config)
                self.logger.info("Gmail collector initialized")
            except Exception as e:
                self.error_handler.handle_error('digest_orchestrator', e, ErrorSeverity.MEDIUM,
                                              {'collector': 'gmail'})
                collectors['gmail'] = None
        else:
            collectors['gmail'] = None

        if MediumCollector:
            try:
                collectors['medium'] = MediumCollector()
                self.logger.info("Medium collector initialized")
            except Exception as e:
                self.error_handler.handle_error('digest_orchestrator', e, ErrorSeverity.MEDIUM,
                                              {'collector': 'medium'})
                collectors['medium'] = None
        else:
            collectors['medium'] = None

        if WeatherCollector:
            try:
                collectors['weather'] = WeatherCollector(self.config)
                self.logger.info("Weather collector initialized")
            except Exception as e:
                self.error_handler.handle_error('digest_orchestrator', e, ErrorSeverity.MEDIUM,
                                              {'collector': 'weather'})
                collectors['weather'] = None
        else:
            collectors['weather'] = None

        return collectors

    async def generate_morning_digest(self, hours_back: int = 24) -> Dict[str, Any]:
        """Generate complete morning digest"""
        self.logger.info(f"Starting morning digest generation for last {hours_back} hours")
        
        start_time = datetime.now()
        
        # Step 1: Collect all data in parallel
        raw_data = await self._collect_all_data(hours_back)
        
        # Step 2: Process with AI agents
        agent_results = await self.agent_coordinator.process_all_data(raw_data, self.context)
        
        # Step 3: Generate final digest
        final_digest = await self._generate_final_digest(agent_results, raw_data)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Step 4: Compile comprehensive result
        result = {
            'digest': final_digest,
            'agent_results': agent_results,
            'raw_data_summary': self._create_data_summary(raw_data),
            'metadata': {
                'generation_time': start_time.isoformat(),
                'completion_time': end_time.isoformat(),
                'duration_seconds': duration,
                'hours_back': hours_back,
                'context': self.context,
                'data_sources_status': self._get_data_sources_status(raw_data)
            },
            'token_usage': self.token_counter.get_usage_summary(days_back=1)['budget_status']
        }
        
        self.logger.info(f"Morning digest generated successfully in {duration:.2f} seconds")
        return result

    async def _collect_all_data(self, hours_back: int) -> Dict[str, Any]:
        """Collect data from all sources in parallel with graceful degradation"""
        self.logger.info("Starting parallel data collection")
        
        # Create collection tasks
        collection_tasks = []
        
        if self.collectors['news']:
            collection_tasks.append(self._collect_with_fallback('news', hours_back))
        
        if self.collectors['calendar']:
            collection_tasks.append(self._collect_with_fallback('calendar', hours_back))
            
        if self.collectors['gmail']:
            collection_tasks.append(self._collect_with_fallback('gmail', hours_back))
            
        if self.collectors['medium']:
            collection_tasks.append(self._collect_with_fallback('medium', hours_back))
            
        if self.collectors['weather']:
            collection_tasks.append(self._collect_with_fallback('weather', hours_back))

        # Run all collections in parallel
        collection_results = await asyncio.gather(*collection_tasks, return_exceptions=True)
        
        # Compile results
        raw_data = {}
        for result in collection_results:
            if isinstance(result, dict) and 'source' in result:
                raw_data[result['source']] = result['data']
            elif isinstance(result, Exception):
                self.logger.error(f"Collection task failed: {result}")
        
        self.logger.info(f"Data collection completed. Sources: {list(raw_data.keys())}")
        return raw_data

    async def _collect_with_fallback(self, source: str, hours_back: int) -> Dict[str, Any]:
        """Collect data from a single source with error handling"""
        try:
            collector = self.collectors[source]
            if not collector:
                return {'source': source, 'data': None, 'error': 'Collector not initialized'}
            
            if source == 'news':
                data = await collector.collect_all_news(hours_back)
            elif source == 'calendar':
                data = await collector.collect_events(hours_back)
            elif source == 'gmail':
                data = await collector.collect_emails(hours_back)
            elif source == 'medium':
                data = await collector.collect_articles(hours_back)
            elif source == 'weather':
                data = await collector.collect_weather_data()
            else:
                raise ValueError(f"Unknown collector source: {source}")
            
            self.logger.info(f"Successfully collected data from {source}")
            return {'source': source, 'data': data, 'error': None}
            
        except Exception as e:
            self.error_handler.handle_async_error(
                'digest_orchestrator', 
                e, 
                ErrorSeverity.MEDIUM,
                {'source': source, 'hours_back': hours_back}
            )
            return {'source': source, 'data': None, 'error': str(e)}

    async def _generate_final_digest(self, agent_results: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final coordinated digest"""
        try:
            # Prepare comprehensive context for master coordinator
            master_context = {
                **self.context,
                'data_freshness': {
                    source: data.get('collection_time') if data else None 
                    for source, data in raw_data.items()
                },
                'agent_processing_status': {
                    agent: bool(result and not result.get('error'))
                    for agent, result in agent_results.items()
                }
            }
            
            # Use master coordinator to synthesize everything
            final_digest = await self.agent_coordinator.coordinate_final_digest(
                agent_results, master_context
            )
            
            return final_digest
            
        except Exception as e:
            self.error_handler.handle_async_error(
                'digest_orchestrator', 
                e, 
                ErrorSeverity.HIGH,
                {'agent_results_keys': list(agent_results.keys())}
            )
            # Fallback: return structured summary of available data
            return self._create_fallback_digest(agent_results, raw_data)

    def _create_fallback_digest(self, agent_results: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback digest when master coordination fails"""
        digest = {
            'title': 'Morning Digest (Fallback Mode)',
            'generated_at': datetime.now().isoformat(),
            'status': 'partial_processing',
            'sections': []
        }
        
        # Add sections based on available data
        if 'norwegian_news' in agent_results and agent_results['norwegian_news']:
            digest['sections'].append({
                'title': 'Norwegian News',
                'content': agent_results['norwegian_news'].get('summary', 'News analysis available'),
                'priority': 'high'
            })
        
        if 'tech_intelligence' in agent_results and agent_results['tech_intelligence']:
            digest['sections'].append({
                'title': 'Technology News',
                'content': agent_results['tech_intelligence'].get('summary', 'Tech analysis available'),
                'priority': 'high'
            })
        
        if 'calendar_intelligence' in agent_results and agent_results['calendar_intelligence']:
            digest['sections'].append({
                'title': 'Today\'s Schedule',
                'content': agent_results['calendar_intelligence'].get('summary', 'Calendar analysis available'),
                'priority': 'high'
            })
        
        if 'newsletter_intelligence' in agent_results and agent_results['newsletter_intelligence']:
            digest['sections'].append({
                'title': 'Newsletter Insights',
                'content': agent_results['newsletter_intelligence'].get('summary', 'Newsletter analysis available'),
                'priority': 'medium'
            })
        
        # Add weather if available
        if 'weather' in raw_data and raw_data['weather']:
            weather_data = raw_data['weather']
            digest['sections'].append({
                'title': 'Weather Update',
                'content': f"Weather data available for {weather_data.get('location', 'your area')}",
                'priority': 'medium'
            })
        
        return digest

    def _create_data_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of collected raw data"""
        summary = {}
        
        for source, data in raw_data.items():
            if data is None:
                summary[source] = {'status': 'failed', 'count': 0}
                continue
                
            if source == 'news':
                total_articles = data.get('total_articles', 0) if data else 0
                summary[source] = {
                    'status': 'success' if total_articles > 0 else 'no_data',
                    'count': total_articles,
                    'categories': list(data.get('articles', {}).keys()) if data else []
                }
            elif source == 'calendar':
                event_count = len(data.get('events', [])) if data else 0
                summary[source] = {
                    'status': 'success' if event_count > 0 else 'no_data',
                    'count': event_count
                }
            elif source == 'gmail':
                email_count = len(data.get('emails', [])) if data else 0
                summary[source] = {
                    'status': 'success' if email_count > 0 else 'no_data',
                    'count': email_count
                }
            elif source == 'medium':
                article_count = len(data.get('articles', [])) if data else 0
                summary[source] = {
                    'status': 'success' if article_count > 0 else 'no_data',
                    'count': article_count
                }
            elif source == 'weather':
                summary[source] = {
                    'status': 'success' if data else 'no_data',
                    'location': data.get('location') if data else None
                }
            else:
                summary[source] = {
                    'status': 'unknown',
                    'has_data': bool(data)
                }
        
        return summary

    def _get_data_sources_status(self, raw_data: Dict[str, Any]) -> Dict[str, str]:
        """Get status of each data source"""
        status = {}
        
        for source, data in raw_data.items():
            if data is None:
                status[source] = 'failed'
            elif isinstance(data, dict) and data.get('error'):
                status[source] = 'error'
            elif self._has_meaningful_data(source, data):
                status[source] = 'success'
            else:
                status[source] = 'no_data'
        
        return status

    def _has_meaningful_data(self, source: str, data: Any) -> bool:
        """Check if data source has meaningful content"""
        if not data or not isinstance(data, dict):
            return False
        
        if source == 'news':
            return data.get('total_articles', 0) > 0
        elif source == 'calendar':
            return len(data.get('events', [])) > 0
        elif source == 'gmail':
            return len(data.get('emails', [])) > 0
        elif source == 'medium':
            return len(data.get('articles', [])) > 0
        elif source == 'weather':
            return bool(data.get('current'))
        
        return bool(data)

    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of orchestrator and all components"""
        status = {
            'orchestrator': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'collectors': {},
            'agents': {},
            'error_summary': self.error_handler.get_error_summary(hours_back=24),
            'token_usage': self.token_counter.get_usage_summary(days_back=1)
        }
        
        # Check collector status
        for name, collector in self.collectors.items():
            if collector is None:
                status['collectors'][name] = 'not_initialized'
            else:
                status['collectors'][name] = 'ready'
        
        # Check agent coordinator status
        status['agents'] = await self.agent_coordinator.get_health_status()
        
        # Overall health assessment
        failed_collectors = sum(1 for s in status['collectors'].values() if s != 'ready')
        total_collectors = len(status['collectors'])
        
        if failed_collectors == 0:
            status['orchestrator'] = 'healthy'
        elif failed_collectors < total_collectors / 2:
            status['orchestrator'] = 'degraded'
        else:
            status['orchestrator'] = 'unhealthy'
        
        return status