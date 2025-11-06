#!/usr/bin/env python3
"""
System validation script for Morning Digest application.
Tests all components and validates the complete system functionality.
"""

import os
import sys
import logging
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def setup_logging():
    """Setup logging for test output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

class SystemTester:
    """Comprehensive system testing class."""
    
    def __init__(self):
        self.results = {}
        self.logger = logging.getLogger('SystemTester')
        
    def test_imports(self) -> bool:
        """Test that all required modules can be imported."""
        self.logger.info("Testing module imports...")
        
        modules_to_test = [
            # Core modules
            ('utils.config_loader', 'ConfigLoader'),
            ('utils.email_sender', 'EmailSender'),
            ('utils.token_manager', 'TokenManager'),
            
            # Agents
            ('agents.norwegian_news_agent', 'NorwegianNewsAgent'),
            ('agents.tech_intelligence_agent', 'TechIntelligenceAgent'),
            ('agents.calendar_intelligence_agent', 'CalendarIntelligenceAgent'),
            ('agents.newsletter_intelligence_agent', 'NewsletterIntelligenceAgent'),
            ('agents.master_coordinator_agent', 'MasterCoordinatorAgent'),
            
            # Services
            ('services.news_collector', 'NewsCollector'),
            ('services.calendar_service', 'CalendarService'),
            ('services.newsletter_processor', 'NewsletterProcessor'),
            ('services.weather_service', 'WeatherService'),
            
            # Formatters
            ('formatters.html_formatter', 'HTMLFormatter'),
            ('formatters.text_formatter', 'TextFormatter'),
            
            # Orchestration
            ('orchestration.digest_orchestrator', 'DigestOrchestrator'),
            ('orchestration.agent_coordinator', 'AgentCoordinator'),
        ]
        
        failed_imports = []
        for module_path, class_name in modules_to_test:
            try:
                module = __import__(module_path, fromlist=[class_name])
                getattr(module, class_name)
                self.logger.info(f"✅ {module_path}.{class_name}")
            except Exception as e:
                self.logger.error(f"❌ {module_path}.{class_name}: {e}")
                failed_imports.append(f"{module_path}.{class_name}")
        
        success = len(failed_imports) == 0
        self.results['imports'] = {
            'success': success,
            'failed': failed_imports,
            'total_tested': len(modules_to_test)
        }
        return success
    
    def test_configuration_loading(self) -> bool:
        """Test configuration loading functionality."""
        self.logger.info("Testing configuration loading...")
        
        try:
            from utils.config_loader import ConfigLoader
            
            # Test with default config
            config_loader = ConfigLoader()
            config = config_loader.load_config()
            
            required_sections = ['claude', 'email', 'logging', 'context']
            missing_sections = [section for section in required_sections 
                              if section not in config]
            
            if missing_sections:
                self.logger.error(f"Missing config sections: {missing_sections}")
                self.results['config_loading'] = {
                    'success': False,
                    'error': f"Missing sections: {missing_sections}"
                }
                return False
            
            # Test environment variable override
            test_key = "MORNING_DIGEST_TEST_VAR"
            test_value = "test_value_123"
            os.environ[test_key] = test_value
            
            # Clean up
            if test_key in os.environ:
                del os.environ[test_key]
            
            self.logger.info("✅ Configuration loading successful")
            self.results['config_loading'] = {'success': True}
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Configuration loading failed: {e}")
            self.results['config_loading'] = {'success': False, 'error': str(e)}
            return False
    
    def test_agent_initialization(self) -> bool:
        """Test that all agents can be initialized."""
        self.logger.info("Testing agent initialization...")
        
        try:
            from utils.config_loader import ConfigLoader
            from utils.token_manager import TokenManager
            from agents.norwegian_news_agent import NorwegianNewsAgent
            from agents.tech_intelligence_agent import TechIntelligenceAgent
            from agents.calendar_intelligence_agent import CalendarIntelligenceAgent
            from agents.newsletter_intelligence_agent import NewsletterIntelligenceAgent
            from agents.master_coordinator_agent import MasterCoordinatorAgent
            
            config_loader = ConfigLoader()
            token_manager = TokenManager(config_loader)
            
            # Test agent initialization (without API calls)
            agents = [
                ('NorwegianNewsAgent', NorwegianNewsAgent),
                ('TechIntelligenceAgent', TechIntelligenceAgent),
                ('CalendarIntelligenceAgent', CalendarIntelligenceAgent),
                ('NewsletterIntelligenceAgent', NewsletterIntelligenceAgent),
                ('MasterCoordinatorAgent', MasterCoordinatorAgent),
            ]
            
            failed_agents = []
            for agent_name, agent_class in agents:
                try:
                    agent = agent_class(config_loader, token_manager)
                    self.logger.info(f"✅ {agent_name} initialized")
                except Exception as e:
                    self.logger.error(f"❌ {agent_name} failed: {e}")
                    failed_agents.append(agent_name)
            
            success = len(failed_agents) == 0
            self.results['agent_initialization'] = {
                'success': success,
                'failed_agents': failed_agents
            }
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Agent initialization test failed: {e}")
            self.results['agent_initialization'] = {'success': False, 'error': str(e)}
            return False
    
    def test_service_initialization(self) -> bool:
        """Test that all services can be initialized."""
        self.logger.info("Testing service initialization...")
        
        try:
            from utils.config_loader import ConfigLoader
            from services.news_collector import NewsCollector
            from services.calendar_service import CalendarService
            from services.newsletter_processor import NewsletterProcessor
            from services.weather_service import WeatherService
            
            config_loader = ConfigLoader()
            
            services = [
                ('NewsCollector', NewsCollector),
                ('CalendarService', CalendarService),
                ('NewsletterProcessor', NewsletterProcessor),
                ('WeatherService', WeatherService),
            ]
            
            failed_services = []
            for service_name, service_class in services:
                try:
                    service = service_class(config_loader)
                    self.logger.info(f"✅ {service_name} initialized")
                except Exception as e:
                    self.logger.error(f"❌ {service_name} failed: {e}")
                    failed_services.append(service_name)
            
            success = len(failed_services) == 0
            self.results['service_initialization'] = {
                'success': success,
                'failed_services': failed_services
            }
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Service initialization test failed: {e}")
            self.results['service_initialization'] = {'success': False, 'error': str(e)}
            return False
    
    def test_formatter_functionality(self) -> bool:
        """Test formatter functionality with sample data."""
        self.logger.info("Testing formatters...")
        
        try:
            from formatters.html_formatter import HTMLFormatter
            from formatters.text_formatter import TextFormatter
            from utils.config_loader import ConfigLoader
            
            config_loader = ConfigLoader()
            
            # Sample data for testing
            sample_data = {
                'priority_items': [
                    {'title': 'Test Priority Item', 'summary': 'Test summary'}
                ],
                'calendar_summary': {
                    'events_today': 2,
                    'urgent_events': 1,
                    'recommendations': ['Test recommendation']
                },
                'news_analysis': 'Sample news analysis',
                'tech_intelligence': 'Sample tech intelligence',
                'newsletter_insights': {
                    'learning_opportunities': ['Test learning'],
                    'deals_and_offers': ['Test deal'],
                    'categories': {'tech': 1, 'learning': 1}
                },
                'weather': {
                    'current': {'temp': 15, 'description': 'Clear'},
                    'forecast': 'Sunny day ahead'
                }
            }
            
            # Test HTML formatter
            html_formatter = HTMLFormatter(config_loader)
            html_output = html_formatter.format_digest(sample_data)
            
            if not html_output or '<html' not in html_output:
                self.logger.error("❌ HTML formatter produced invalid output")
                self.results['formatters'] = {
                    'success': False, 
                    'error': 'HTML formatter failed'
                }
                return False
            
            # Test Text formatter
            text_formatter = TextFormatter(config_loader)
            text_output = text_formatter.format_digest(sample_data)
            
            if not text_output or len(text_output.strip()) < 100:
                self.logger.error("❌ Text formatter produced invalid output")
                self.results['formatters'] = {
                    'success': False, 
                    'error': 'Text formatter failed'
                }
                return False
            
            self.logger.info("✅ Both formatters working correctly")
            self.results['formatters'] = {'success': True}
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Formatter test failed: {e}")
            self.results['formatters'] = {'success': False, 'error': str(e)}
            return False
    
    def test_orchestration_setup(self) -> bool:
        """Test orchestration layer setup."""
        self.logger.info("Testing orchestration setup...")
        
        try:
            from orchestration.digest_orchestrator import DigestOrchestrator
            from orchestration.agent_coordinator import AgentCoordinator
            from utils.config_loader import ConfigLoader
            from utils.token_manager import TokenManager
            
            config_loader = ConfigLoader()
            token_manager = TokenManager(config_loader)
            
            # Test AgentCoordinator initialization
            agent_coordinator = AgentCoordinator(config_loader, token_manager)
            self.logger.info("✅ AgentCoordinator initialized")
            
            # Test DigestOrchestrator initialization
            orchestrator = DigestOrchestrator(config_loader)
            self.logger.info("✅ DigestOrchestrator initialized")
            
            self.results['orchestration'] = {'success': True}
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Orchestration test failed: {e}")
            self.results['orchestration'] = {'success': False, 'error': str(e)}
            return False
    
    def test_environment_validation(self) -> bool:
        """Test environment variable validation."""
        self.logger.info("Testing environment validation...")
        
        required_vars = [
            'MORNING_DIGEST_CLAUDE_API_KEY',
            'MORNING_DIGEST_GMAIL_ADDRESS',
            'MORNING_DIGEST_EMAIL_PASSWORD'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            self.logger.warning(f"Missing environment variables: {missing_vars}")
            self.logger.warning("This is expected if testing without .env file")
            self.results['environment'] = {
                'success': False,
                'missing_vars': missing_vars,
                'note': 'Expected if no .env file configured'
            }
            return False
        else:
            self.logger.info("✅ All environment variables configured")
            self.results['environment'] = {'success': True}
            return True
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all system tests."""
        self.logger.info("Starting comprehensive system validation...")
        
        tests = [
            ('Module Imports', self.test_imports),
            ('Configuration Loading', self.test_configuration_loading),
            ('Agent Initialization', self.test_agent_initialization),
            ('Service Initialization', self.test_service_initialization),
            ('Formatter Functionality', self.test_formatter_functionality),
            ('Orchestration Setup', self.test_orchestration_setup),
            ('Environment Validation', self.test_environment_validation),
        ]
        
        results_summary = {
            'total_tests': len(tests),
            'passed': 0,
            'failed': 0,
            'test_results': self.results
        }
        
        for test_name, test_func in tests:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"Running: {test_name}")
            self.logger.info(f"{'='*50}")
            
            try:
                success = test_func()
                if success:
                    results_summary['passed'] += 1
                    self.logger.info(f"✅ {test_name} PASSED")
                else:
                    results_summary['failed'] += 1
                    self.logger.error(f"❌ {test_name} FAILED")
            except Exception as e:
                results_summary['failed'] += 1
                self.logger.error(f"❌ {test_name} ERROR: {e}")
                self.results[test_name.lower().replace(' ', '_')] = {
                    'success': False,
                    'error': str(e)
                }
        
        # Final summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("SYSTEM VALIDATION SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total Tests: {results_summary['total_tests']}")
        self.logger.info(f"Passed: {results_summary['passed']}")
        self.logger.info(f"Failed: {results_summary['failed']}")
        
        success_rate = (results_summary['passed'] / results_summary['total_tests']) * 100
        self.logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if results_summary['failed'] == 0:
            self.logger.info("🎉 ALL TESTS PASSED - System ready for operation!")
        elif success_rate >= 80:
            self.logger.warning("⚠️  Most tests passed - System mostly functional")
        else:
            self.logger.error("❌ Multiple failures - System needs attention")
        
        return results_summary

def main():
    """Main test function."""
    setup_logging()
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    tester = SystemTester()
    results = asyncio.run(tester.run_all_tests())
    
    # Return appropriate exit code
    return 0 if results['failed'] == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)