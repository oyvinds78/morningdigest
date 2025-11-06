#!/usr/bin/env python3
"""
GitHub repository setup script for Morning Digest.
Helps configure GitHub repository with required secrets and settings.
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

def setup_logging():
    """Setup logging for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

class GitHubSetupHelper:
    """Helper class for GitHub repository setup."""
    
    def __init__(self):
        self.logger = logging.getLogger('GitHubSetup')
        
    def check_github_cli(self) -> bool:
        """Check if GitHub CLI is installed and authenticated."""
        try:
            import subprocess
            result = subprocess.run(['gh', 'auth', 'status'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.logger.info("✅ GitHub CLI is installed and authenticated")
                return True
            else:
                self.logger.error("❌ GitHub CLI authentication failed")
                self.logger.error("Run: gh auth login")
                return False
        except FileNotFoundError:
            self.logger.error("❌ GitHub CLI not found")
            self.logger.error("Install from: https://cli.github.com/")
            return False
        except Exception as e:
            self.logger.error(f"❌ Error checking GitHub CLI: {e}")
            return False
    
    def get_required_secrets(self) -> Dict[str, Dict[str, str]]:
        """Get list of required GitHub secrets with descriptions."""
        return {
            "CLAUDE_API_KEY": {
                "description": "Claude API key from Anthropic",
                "example": "sk-ant-api03-...",
                "required": True,
                "source": "https://console.anthropic.com/"
            },
            "GMAIL_ADDRESS": {
                "description": "Gmail address for sending digest emails",
                "example": "your-email@gmail.com",
                "required": True,
                "source": "Your Gmail account"
            },
            "GMAIL_APP_PASSWORD": {
                "description": "Gmail app password (not regular password)",
                "example": "xxxx xxxx xxxx xxxx",
                "required": True,
                "source": "Gmail > Security > App Passwords"
            },
            "RECIPIENT_EMAIL": {
                "description": "Email address to receive digest (optional, defaults to GMAIL_ADDRESS)",
                "example": "recipient@example.com",
                "required": False,
                "source": "Any valid email address"
            },
            "OPENWEATHER_API_KEY": {
                "description": "OpenWeather API key for weather data (optional)",
                "example": "abcd1234...",
                "required": False,
                "source": "https://openweathermap.org/api"
            }
        }
    
    def get_repository_variables(self) -> Dict[str, Dict[str, str]]:
        """Get list of repository variables (non-sensitive configuration)."""
        return {
            "TOKEN_BUDGET": {
                "description": "Daily Claude API token budget",
                "default": "10000",
                "example": "15000"
            },
            "HOURLY_TOKEN_LIMIT": {
                "description": "Hourly token usage limit",
                "default": "2000",
                "example": "3000"
            },
            "LOG_LEVEL": {
                "description": "Logging level for the application",
                "default": "INFO",
                "example": "DEBUG"
            },
            "LOCATION": {
                "description": "Location for weather and local context",
                "default": "Trondheim, Norway",
                "example": "Oslo, Norway"
            },
            "TIMEZONE": {
                "description": "Timezone for scheduling and timestamps",
                "default": "Europe/Oslo",
                "example": "Europe/Oslo"
            }
        }
    
    def print_secrets_setup_guide(self):
        """Print detailed guide for setting up GitHub secrets."""
        secrets = self.get_required_secrets()
        
        self.logger.info("🔐 GitHub Secrets Setup Guide")
        self.logger.info("=" * 50)
        
        self.logger.info("\n1. Go to your GitHub repository")
        self.logger.info("2. Navigate to Settings > Secrets and variables > Actions")
        self.logger.info("3. Click 'New repository secret' for each required secret:")
        
        for secret_name, info in secrets.items():
            status = "REQUIRED" if info["required"] else "OPTIONAL"
            self.logger.info(f"\n   📋 {secret_name} ({status})")
            self.logger.info(f"      Description: {info['description']}")
            self.logger.info(f"      Example: {info['example']}")
            self.logger.info(f"      Source: {info['source']}")
    
    def print_variables_setup_guide(self):
        """Print guide for setting up repository variables."""
        variables = self.get_repository_variables()
        
        self.logger.info("\n⚙️ GitHub Variables Setup Guide")
        self.logger.info("=" * 50)
        
        self.logger.info("\n1. Go to your GitHub repository")
        self.logger.info("2. Navigate to Settings > Secrets and variables > Actions")
        self.logger.info("3. Click the 'Variables' tab")
        self.logger.info("4. Click 'New repository variable' for each configuration:")
        
        for var_name, info in variables.items():
            self.logger.info(f"\n   🔧 {var_name}")
            self.logger.info(f"      Description: {info['description']}")
            self.logger.info(f"      Default: {info['default']}")
            self.logger.info(f"      Example: {info['example']}")
    
    def generate_setup_commands(self) -> List[str]:
        """Generate GitHub CLI commands for setting up secrets."""
        commands = []
        secrets = self.get_required_secrets()
        
        commands.append("# GitHub CLI commands to set secrets:")
        commands.append("# Replace <value> with your actual values")
        commands.append("")
        
        for secret_name, info in secrets.items():
            if info["required"]:
                commands.append(f"gh secret set {secret_name} --body '<your_{secret_name.lower()}>'")
            else:
                commands.append(f"# Optional: gh secret set {secret_name} --body '<your_{secret_name.lower()}>'")
        
        commands.append("")
        commands.append("# GitHub CLI commands to set variables:")
        variables = self.get_repository_variables()
        
        for var_name, info in variables.items():
            commands.append(f"gh variable set {var_name} --body '{info['default']}'")
        
        return commands
    
    def create_setup_script(self):
        """Create a shell script for easy GitHub setup."""
        commands = self.generate_setup_commands()
        
        script_content = """#!/bin/bash
# GitHub Setup Script for Morning Digest
# This script helps you set up the required secrets and variables

echo "🚀 Morning Digest GitHub Setup"
echo "================================"
echo ""

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not found. Please install it from https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub CLI. Please run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is ready"
echo ""

# Function to prompt for secret
set_secret() {
    local secret_name=$1
    local description=$2
    local required=$3
    
    echo "📋 Setting $secret_name"
    echo "   Description: $description"
    
    if [ "$required" = "true" ]; then
        echo "   Status: REQUIRED"
        read -s -p "   Enter value: " secret_value
        echo ""
        
        if [ -n "$secret_value" ]; then
            gh secret set "$secret_name" --body "$secret_value"
            echo "   ✅ $secret_name set successfully"
        else
            echo "   ❌ $secret_name is required but no value provided"
            return 1
        fi
    else
        echo "   Status: OPTIONAL"
        read -p "   Enter value (or press Enter to skip): " secret_value
        
        if [ -n "$secret_value" ]; then
            gh secret set "$secret_name" --body "$secret_value"
            echo "   ✅ $secret_name set successfully"
        else
            echo "   ⏭️  $secret_name skipped"
        fi
    fi
    echo ""
}

# Function to set variable
set_variable() {
    local var_name=$1
    local description=$2
    local default_value=$3
    
    echo "🔧 Setting $var_name"
    echo "   Description: $description"
    echo "   Default: $default_value"
    
    read -p "   Enter value (or press Enter for default): " var_value
    
    if [ -n "$var_value" ]; then
        gh variable set "$var_name" --body "$var_value"
        echo "   ✅ $var_name set to: $var_value"
    else
        gh variable set "$var_name" --body "$default_value"
        echo "   ✅ $var_name set to default: $default_value"
    fi
    echo ""
}

echo "Setting up GitHub Secrets..."
echo "============================"
"""

        secrets = self.get_required_secrets()
        for secret_name, info in secrets.items():
            script_content += f'set_secret "{secret_name}" "{info["description"]}" "{str(info["required"]).lower()}"\n'
        
        script_content += '''
echo "Setting up GitHub Variables..."
echo "=============================="
'''
        
        variables = self.get_repository_variables()
        for var_name, info in variables.items():
            script_content += f'set_variable "{var_name}" "{info["description"]}" "{info["default"]}"\n'
        
        script_content += '''
echo "🎉 GitHub setup completed!"
echo ""
echo "Next steps:"
echo "1. Verify your secrets and variables in GitHub repository settings"
echo "2. Test the workflow with: gh workflow run daily-digest.yml --ref main"
echo "3. Check the workflow results in the Actions tab"
'''
        
        script_path = Path("scripts/github_setup.sh")
        script_path.write_text(script_content)
        os.chmod(script_path, 0o755)
        
        self.logger.info(f"✅ Created interactive setup script: {script_path}")
        self.logger.info("Run it with: ./scripts/github_setup.sh")
    
    def validate_workflow_file(self) -> bool:
        """Validate that the GitHub workflow file exists and is properly formatted."""
        workflow_path = Path(".github/workflows/daily-digest.yml")
        
        if not workflow_path.exists():
            self.logger.error(f"❌ Workflow file not found: {workflow_path}")
            return False
        
        try:
            import yaml
            content = yaml.safe_load(workflow_path.read_text())
            
            required_keys = ['name', 'on', 'jobs']
            for key in required_keys:
                if key not in content:
                    self.logger.error(f"❌ Missing required key in workflow: {key}")
                    return False
            
            self.logger.info("✅ Workflow file is valid")
            return True
            
        except ImportError:
            # PyYAML not installed, skip validation
            self.logger.info("⚠️  PyYAML not available, skipping workflow validation")
            return True
        except Exception as e:
            self.logger.error(f"❌ Error validating workflow file: {e}")
            return False
    
    def print_final_instructions(self):
        """Print final setup instructions."""
        self.logger.info("\n🎯 Final Setup Instructions")
        self.logger.info("=" * 50)
        
        instructions = [
            "1. Set up GitHub secrets and variables (see guides above)",
            "2. Push your code to GitHub repository",
            "3. Enable GitHub Actions in repository settings",
            "4. Test the workflow manually:",
            "   - Go to Actions tab in your repository",
            "   - Click 'Daily Morning Digest' workflow",
            "   - Click 'Run workflow' button",
            "   - Enable 'Dry run' for testing",
            "5. Check workflow results and logs",
            "6. Once working, the digest will run automatically at 6 AM Norwegian time"
        ]
        
        for instruction in instructions:
            self.logger.info(f"   {instruction}")
        
        self.logger.info("\n📚 Additional Resources:")
        self.logger.info("   - GitHub Actions docs: https://docs.github.com/en/actions")
        self.logger.info("   - GitHub CLI docs: https://cli.github.com/manual/")
        self.logger.info("   - Workflow troubleshooting: Check Actions tab for logs")

def main():
    """Main setup function."""
    setup_logging()
    
    helper = GitHubSetupHelper()
    
    helper.logger.info("🚀 Morning Digest GitHub Setup")
    helper.logger.info("=" * 50)
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    # Check prerequisites
    helper.logger.info("Checking prerequisites...")
    
    # Validate workflow file
    if not helper.validate_workflow_file():
        return False
    
    # Check GitHub CLI (optional but recommended)
    gh_cli_available = helper.check_github_cli()
    
    # Print setup guides
    helper.print_secrets_setup_guide()
    helper.print_variables_setup_guide()
    
    # Create interactive setup script if GitHub CLI is available
    if gh_cli_available:
        helper.create_setup_script()
    else:
        helper.logger.info("\n💡 Install GitHub CLI for automated setup script")
    
    # Print final instructions
    helper.print_final_instructions()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)