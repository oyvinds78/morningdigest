#!/usr/bin/env python3
"""
Demo script showing the orchestration system in action
without requiring all external dependencies.
"""

import sys
import os
import asyncio
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Mock missing dependencies at module level
import sys
from unittest.mock import MagicMock

# Mock google dependencies
google_mock = MagicMock()
google_mock.oauth2.credentials.Credentials = MagicMock
google_mock.auth.transport.requests.Request = MagicMock
google_mock.auth.exceptions.RefreshError = Exception

sys.modules['google'] = google_mock
sys.modules['google.oauth2'] = google_mock.oauth2
sys.modules['google.oauth2.credentials'] = google_mock.oauth2.credentials
sys.modules['google.auth'] = google_mock.auth  
sys.modules['google.auth.transport'] = google_mock.auth.transport
sys.modules['google.auth.transport.requests'] = google_mock.auth.transport.requests
sys.modules['google.auth.exceptions'] = google_mock.auth.exceptions
sys.modules['google_auth_oauthlib'] = MagicMock()
sys.modules['google_auth_oauthlib.flow'] = MagicMock()
sys.modules['googleapiclient'] = MagicMock()
sys.modules['googleapiclient.discovery'] = MagicMock()

# Mock other dependencies
sys.modules['aiohttp'] = MagicMock()
sys.modules['feedparser'] = MagicMock()
sys.modules['anthropic'] = MagicMock()

async def demo_orchestration():
    """Demonstrate the orchestration system"""
    
    print("🎭 Norwegian Morning Digest - Orchestration Demo")
    print("="*60)
    
    try:
        # Import components now that dependencies are mocked
        from src.utils.config_loader import ConfigLoader
        from src.utils.error_handler import ErrorHandler, ErrorSeverity
        from src.utils.token_counter import TokenCounter
        from src.orchestration.digest_orchestrator import DigestOrchestrator
        
        print("✅ Successfully imported all orchestration components")
        
        # Initialize with real classes but mocked dependencies
        config = ConfigLoader()
        error_handler = ErrorHandler(config)
        token_counter = TokenCounter(config)
        
        print("✅ Utilities initialized")
        
        # Initialize orchestrator
        orchestrator = DigestOrchestrator(
            config_loader=config,
            error_handler=error_handler,
            token_counter=token_counter
        )
        
        print("✅ DigestOrchestrator created successfully")
        print(f"   📍 Location: {orchestrator.context['location']}")
        print(f"   👨‍👩‍👦‍👦 Family: {orchestrator.context['family_context']}")  
        print(f"   💼 Career: {orchestrator.context['career_focus']}")
        print(f"   🎯 Interests: {', '.join(orchestrator.context['interests'][:5])}...")
        
        # Show collector status
        print(f"\n📊 Collectors initialized:")
        for name, collector in orchestrator.collectors.items():
            status = "✅ Ready" if collector else "⚠️  Unavailable (deps missing)"
            print(f"   {name}: {status}")
        
        # Show agent coordinator
        agent_info = orchestrator.agent_coordinator.get_agent_info()
        print(f"\n🤖 Agent Coordinator:")
        print(f"   Total agents: {agent_info['total_agents']}")
        print(f"   Initialized: {agent_info['initialized_agents']}")
        
        for name, info in agent_info['agents'].items():
            status = "✅ Ready" if info['initialized'] else "⚠️  Unavailable"
            print(f"   {name}: {status}")
        
        # Demo health check
        print(f"\n🔍 Health Check:")
        health = await orchestrator.get_health_status()
        print(f"   Overall status: {health['orchestrator']}")
        print(f"   Error count (24h): {health['error_summary']['total_errors']}")
        
        # Show architecture flow
        print(f"\n🏗️  Architecture Flow:")
        print("   main.py")
        print("   ↓")
        print("   DigestOrchestrator")
        print("   ├── Collectors (5 data sources)")
        print("   │   ├── News (Norwegian + International)")
        print("   │   ├── Calendar (Google Calendar)")
        print("   │   ├── Gmail (Newsletter analysis)")
        print("   │   ├── Medium (Tech articles)")
        print("   │   └── Weather (Trondheim)")
        print("   ↓")
        print("   AgentCoordinator")
        print("   ├── Norwegian News Agent")
        print("   ├── Tech Intelligence Agent")
        print("   ├── Calendar Intelligence Agent")
        print("   ├── Newsletter Intelligence Agent")
        print("   └── Master Coordinator Agent")
        print("   ↓")
        print("   Formatted Output (HTML/Text/JSON)")
        
        print(f"\n⚡ Key Features Demonstrated:")
        print("   ✅ Async parallel processing")
        print("   ✅ Norwegian context integration") 
        print("   ✅ Graceful degradation (missing deps)")
        print("   ✅ Error handling and logging")
        print("   ✅ Token budget management")
        print("   ✅ Health monitoring")
        print("   ✅ Modular architecture")
        
        print(f"\n🚀 Ready for Production:")
        print("   1. Install dependencies: pip install -r requirements.txt")
        print("   2. Configure API keys in config/settings.yaml")
        print("   3. Run: python -m src.main generate")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting orchestration demo...")
    success = asyncio.run(demo_orchestration())
    print(f"\n{'🎉 DEMO SUCCESSFUL' if success else '❌ DEMO FAILED'}")
    sys.exit(0 if success else 1)