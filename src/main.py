#!/usr/bin/env python3
"""
Norwegian Morning Digest AI System
Main entry point with CLI interface

Usage:
    python -m src.main generate [--hours=24] [--format=html|text|json] [--output=file]
    python -m src.main health
    python -m src.main status  
    python -m src.main test-agents
    python -m src.main send-email [--format=html]
"""

import asyncio
import sys
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import utilities with graceful fallback
try:
    from .utils.config_loader import ConfigLoader
    from .utils.error_handler import ErrorHandler, ErrorSeverity
    from .utils.token_counter import TokenCounter
    from .utils.email_sender import EmailSender
except ImportError as e:
    print(f"Error importing utilities: {e}")
    sys.exit(1)

try:
    from .orchestration.digest_orchestrator import DigestOrchestrator
except ImportError as e:
    print(f"Error importing orchestrator: {e}")
    sys.exit(1)

# Import formatters with graceful fallback
try:
    from .formatters.html_formatter import HTMLFormatter
except ImportError:
    HTMLFormatter = None
    print("Warning: HTMLFormatter unavailable")

try:
    from .formatters.text_formatter import TextFormatter
except ImportError:
    TextFormatter = None
    print("Warning: TextFormatter unavailable")

try:
    from .formatters.json_formatter import JSONFormatter
except ImportError:
    JSONFormatter = None
    print("Warning: JSONFormatter unavailable")


class SimpleFormatter:
    """Fallback formatter when others are unavailable"""
    def format(self, digest_data: Dict[str, Any]) -> str:
        """Simple text formatting"""
        output = []
        output.append("=== Norwegian Morning Digest ===")
        output.append(f"Generated: {digest_data.get('metadata', {}).get('generation_time', 'Unknown')}")
        
        digest = digest_data.get('digest', {})
        if isinstance(digest, dict):
            if digest.get('title'):
                output.append(f"\nTitle: {digest['title']}")
            
            sections = digest.get('sections', [])
            for section in sections:
                if isinstance(section, dict):
                    output.append(f"\n--- {section.get('title', 'Section')} ---")
                    output.append(section.get('content', 'No content available'))
        
        # Add data summary
        raw_summary = digest_data.get('raw_data_summary', {})
        if raw_summary:
            output.append("\n--- Data Collection Summary ---")
            for source, info in raw_summary.items():
                status = info.get('status', 'unknown')
                count = info.get('count', 0)
                output.append(f"{source}: {count} items ({status})")
        
        return "\n".join(output)


class MorningDigestCLI:
    def __init__(self):
        self.setup_logging()
        self.config = ConfigLoader()
        self.error_handler = ErrorHandler(self.config)
        self.token_counter = TokenCounter(self.config)
        self.email_sender = EmailSender(self.config)
        
        # Initialize orchestrator
        self.orchestrator = DigestOrchestrator(
            config_loader=self.config,
            error_handler=self.error_handler,
            token_counter=self.token_counter
        )
        
        # Initialize formatters
        self.formatters = {}
        
        if HTMLFormatter:
            try:
                self.formatters['html'] = HTMLFormatter(self.config)
            except Exception as e:
                print(f"Warning: Failed to initialize HTMLFormatter: {e}")
        
        if TextFormatter:
            try:
                self.formatters['text'] = TextFormatter(self.config)
            except Exception as e:
                print(f"Warning: Failed to initialize TextFormatter: {e}")
        
        if JSONFormatter:
            try:
                self.formatters['json'] = JSONFormatter(self.config)
            except Exception as e:
                print(f"Warning: Failed to initialize JSONFormatter: {e}")
        
        # Fallback formatter for when nothing else works
        if not self.formatters:
            print("Warning: No formatters available, using fallback")
            self.formatters['text'] = SimpleFormatter()
        
        self.logger = logging.getLogger('morning_digest_cli')

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/morning_digest.log', encoding='utf-8')
            ]
        )

    async def generate_digest(self, hours: int = 24, format_type: str = 'html', output: Optional[str] = None) -> bool:
        """Generate morning digest"""
        try:
            self.logger.info(f"Starting digest generation (hours={hours}, format={format_type})")
            print(f"Starting Norwegian Morning Digest for last {hours} hours...")
            
            # Generate digest
            digest_data = await self.orchestrator.generate_morning_digest(hours_back=hours)
            
            # Format digest
            formatter = self.formatters.get(format_type)
            if not formatter:
                print(f"Error: Unknown format: {format_type}")
                return False
            
            formatted_content = formatter.format(digest_data)
            
            # Output handling
            if output:
                output_path = Path(output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_content)
                
                print(f"Success: Digest saved to: {output_path}")
                print(f"Stats: Generation took {digest_data['metadata']['duration_seconds']:.2f} seconds")
                print(f"Token usage: {digest_data.get('token_usage', {}).get('daily_used', 'N/A')} tokens today")
            else:
                # Print to console
                print("\n" + "="*60)
                print(formatted_content)
                print("="*60)
            
            # Print summary
            self._print_generation_summary(digest_data)
            
            return True
            
        except Exception as e:
            self.error_handler.handle_error('main_cli', e, ErrorSeverity.CRITICAL)
            print(f"Error: Failed to generate digest: {e}")
            return False

    async def send_email_digest(self, format_type: str = 'html') -> bool:
        """Generate and send digest via email"""
        try:
            print("Generating and sending morning digest email...")
            
            # Generate digest
            digest_data = await self.orchestrator.generate_morning_digest()
            
            # Format for email
            formatter = self.formatters.get(format_type, self.formatters['html'])
            formatted_content = formatter.format(digest_data)
            
            # Send email
            success = self.email_sender.send_digest(
                content=formatted_content,
                format_type=format_type,
                metadata=digest_data['metadata']
            )
            
            if success:
                print("Success: Morning digest sent successfully!")
                self._print_generation_summary(digest_data)
                return True
            else:
                print("Error: Failed to send email digest")
                return False
                
        except Exception as e:
            self.error_handler.handle_error('main_cli', e, ErrorSeverity.HIGH)
            print(f"Error: Failed to send email digest: {e}")
            return False

    async def health_check(self) -> bool:
        """Perform comprehensive health check"""
        try:
            print("Performing system health check...")
            
            health_status = await self.orchestrator.get_health_status()
            
            print(f"\nSystem Health Report - {health_status['timestamp']}")
            print("="*50)
            
            # Overall status
            orchestrator_status = health_status['orchestrator']
            status_emoji = {"healthy": "OK", "degraded": "WARN", "unhealthy": "ERROR"}
            print(f"Overall Status: {status_emoji.get(orchestrator_status, '?')} {orchestrator_status.upper()}")
            
            # Collectors status
            print("\nData Collectors:")
            for collector, status in health_status['collectors'].items():
                status_icon = "OK" if status == "ready" else "ERROR"
                print(f"  {status_icon} {collector}: {status}")
            
            # Agents status
            print("\nAI Agents:")
            agents_status = health_status['agents']
            if 'agents' in agents_status:
                for agent, info in agents_status['agents'].items():
                    agent_status = info.get('status', 'unknown')
                    status_icon = "OK" if agent_status == "healthy" else "ERROR"
                    print(f"  {status_icon} {agent}: {agent_status}")
            
            # Error summary
            error_summary = health_status['error_summary']
            print(f"\nRecent Errors (24h): {error_summary['total_errors']}")
            if error_summary['total_errors'] > 0:
                for severity, count in error_summary['severity_breakdown'].items():
                    if count > 0:
                        print(f"  {severity}: {count}")
            
            # Token usage
            token_usage = health_status['token_usage']
            budget_status = token_usage.get('budget_status', {})
            print(f"\nToken Usage Today:")
            print(f"  Daily: {budget_status.get('daily_used', 0)}/{budget_status.get('daily_limit', 'N/A')}")
            print(f"  Hourly: {budget_status.get('hourly_used', 0)}/{budget_status.get('hourly_limit', 'N/A')}")
            
            return orchestrator_status in ['healthy', 'degraded']
            
        except Exception as e:
            self.error_handler.handle_error('main_cli', e, ErrorSeverity.HIGH)
            print(f"Error: Health check failed: {e}")
            return False

    async def system_status(self) -> bool:
        """Show detailed system status"""
        try:
            print("System Status Report")
            print("="*40)
            
            # Configuration status
            print("\nConfiguration:")
            print(f"  Config file: {self.config.config_file}")
            print(f"  Claude API: {'Configured' if self.config.get('claude.api_key') else 'Missing'}")
            print(f"  Email: {'Configured' if self.config.get('email.smtp_server') else 'Not configured'}")
            
            # Token counter status
            token_summary = self.token_counter.get_usage_summary(days_back=1)
            print(f"\nToken Usage (24h):")
            print(f"  Total tokens: {token_summary['total_tokens']}")
            print(f"  Total cost: ${token_summary['total_cost_usd']:.4f}")
            print(f"  Requests: {token_summary['total_requests']}")
            
            # Component breakdown
            if token_summary['component_breakdown']:
                print("\n  By component:")
                for component, stats in token_summary['component_breakdown'].items():
                    print(f"    {component}: {stats['total_tokens']} tokens (${stats['total_cost']:.4f})")
            
            # Error summary
            error_summary = self.error_handler.get_error_summary(hours_back=24)
            print(f"\nError Summary (24h):")
            print(f"  Total errors: {error_summary['total_errors']}")
            print(f"  Error rate: {error_summary['error_rate_per_hour']:.2f} errors/hour")
            
            if error_summary['most_common_errors']:
                print("\n  Most common errors:")
                for error in error_summary['most_common_errors'][:3]:
                    print(f"    {error['component']}:{error['error_type']} ({error['count']}x)")
            
            return True
            
        except Exception as e:
            print(f"Error: Failed to get system status: {e}")
            return False

    async def test_agents(self) -> bool:
        """Test all AI agents individually"""
        try:
            print("Testing AI Agents...")
            
            agent_info = self.orchestrator.agent_coordinator.get_agent_info()
            print(f"\nAgent Overview: {agent_info['initialized_agents']}/{agent_info['total_agents']} initialized")
            
            # Test each agent
            test_data = {
                'test': True,
                'content': 'This is a test message for agent validation',
                'timestamp': datetime.now().isoformat()
            }
            test_context = {'test_mode': True, 'location': 'Trondheim, Norway'}
            
            for agent_name in agent_info['agents'].keys():
                print(f"\nTesting {agent_name}...")
                
                if not agent_info['agents'][agent_name]['initialized']:
                    print(f"  ERROR: Not initialized")
                    continue
                
                try:
                    result = await self.orchestrator.agent_coordinator.process_single_agent(
                        agent_name, test_data, test_context
                    )
                    
                    if result.get('error'):
                        print(f"  ERROR: {result['error']}")
                    else:
                        print(f"  OK: Working - Response received")
                        
                except Exception as e:
                    print(f"  ERROR: Exception: {e}")
            
            return True
            
        except Exception as e:
            print(f"Error: Agent testing failed: {e}")
            return False

    def _print_generation_summary(self, digest_data: Dict[str, Any]):
        """Print summary of digest generation"""
        metadata = digest_data.get('metadata', {})
        raw_data_summary = digest_data.get('raw_data_summary', {})
        
        print(f"\nGeneration Summary:")
        print(f"  Duration: {metadata.get('duration_seconds', 0):.2f} seconds")
        print(f"  Data sources:")
        
        for source, summary in raw_data_summary.items():
            status = summary.get('status', 'unknown')
            count = summary.get('count', 0)
            status_icon = "OK" if status == "success" else "WARN" if status == "no_data" else "ERROR"
            print(f"    {status_icon} {source}: {count} items ({status})")

def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser"""
    parser = argparse.ArgumentParser(
        description="Norwegian Morning Digest AI System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main generate                    # Generate HTML digest
  python -m src.main generate --hours=12 --format=text
  python -m src.main generate --output=digest.html
  python -m src.main send-email                  # Generate and email digest
  python -m src.main health                      # System health check
  python -m src.main status                      # Detailed status report
  python -m src.main test-agents                 # Test all AI agents
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate morning digest')
    generate_parser.add_argument('--hours', type=int, default=24, 
                               help='Hours back to collect data (default: 24)')
    generate_parser.add_argument('--format', choices=['html', 'text', 'json'], default='html',
                               help='Output format (default: html)')
    generate_parser.add_argument('--output', type=str,
                               help='Output file path (default: print to console)')
    
    # Send email command
    email_parser = subparsers.add_parser('send-email', help='Generate and send digest via email')
    email_parser.add_argument('--format', choices=['html', 'text'], default='html',
                            help='Email format (default: html)')
    
    # Health command
    subparsers.add_parser('health', help='Perform system health check')
    
    # Status command
    subparsers.add_parser('status', help='Show detailed system status')
    
    # Test agents command
    subparsers.add_parser('test-agents', help='Test all AI agents')
    
    return parser

async def main():
    """Main entry point"""
    parser = create_cli_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        cli = MorningDigestCLI()
        
        if args.command == 'generate':
            success = await cli.generate_digest(
                hours=args.hours,
                format_type=args.format,
                output=args.output
            )
        elif args.command == 'send-email':
            success = await cli.send_email_digest(format_type=args.format)
        elif args.command == 'health':
            success = await cli.health_check()
        elif args.command == 'status':
            success = await cli.system_status()
        elif args.command == 'test-agents':
            success = await cli.test_agents()
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    # Ensure logs directory exists
    Path("logs").mkdir(exist_ok=True)
    
    # Run main
    exit_code = asyncio.run(main())
    sys.exit(exit_code)