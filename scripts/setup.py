#!/usr/bin/env python3
"""
Setup script for Morning Digest application.
Creates necessary directories, validates configuration, and sets up the environment.
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Tuple

def setup_logging():
    """Setup basic logging for the setup process."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def create_directories() -> List[str]:
    """Create necessary directories for the application."""
    directories = [
        'logs',
        'data',
        'data/news',
        'data/calendar',
        'data/newsletters',
        'temp'
    ]
    
    created = []
    for directory in directories:
        dir_path = Path(directory)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            created.append(str(dir_path))
            logging.info(f"Created directory: {directory}")
        else:
            logging.info(f"Directory already exists: {directory}")
    
    return created

def validate_environment_variables() -> Tuple[bool, List[str]]:
    """Validate that required environment variables are set."""
    required_vars = [
        'MORNING_DIGEST_CLAUDE_API_KEY',
        'MORNING_DIGEST_GMAIL_ADDRESS',
        'MORNING_DIGEST_EMAIL_PASSWORD'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    return len(missing) == 0, missing

def validate_config_files() -> Tuple[bool, List[str]]:
    """Validate that required configuration files exist."""
    config_files = [
        'config/settings.yaml',
        'config/email_template.html'
    ]
    
    missing = []
    for file_path in config_files:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    return len(missing) == 0, missing

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if required Python packages are installed."""
    required_packages = [
        'anthropic',
        'pyyaml',
        'python-dotenv',
        'requests',
        'beautifulsoup4',
        'feedparser',
        'pytz'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    return len(missing) == 0, missing

def create_env_example():
    """Create .env.example file if it doesn't exist."""
    env_example_path = Path('.env.example')
    
    if not env_example_path.exists():
        env_content = """# Morning Digest Environment Variables
# Copy this file to .env and fill in your actual values

# Claude AI API Key (required)
MORNING_DIGEST_CLAUDE_API_KEY=your_claude_api_key_here

# Email Configuration (required for email sending)
MORNING_DIGEST_GMAIL_ADDRESS=your_email@gmail.com
MORNING_DIGEST_EMAIL_PASSWORD=your_app_password_here

# Optional API Keys
MORNING_DIGEST_OPENWEATHER_API_KEY=your_openweather_api_key

# Optional Configuration Overrides
# MORNING_DIGEST_LOG_LEVEL=INFO
# MORNING_DIGEST_TOKEN_BUDGET=10000
"""
        env_example_path.write_text(env_content)
        logging.info("Created .env.example file")
    else:
        logging.info(".env.example already exists")

def setup_gitignore():
    """Ensure .gitignore includes necessary entries."""
    gitignore_path = Path('.gitignore')
    
    required_entries = [
        '.env',
        '*.log',
        'logs/',
        'temp/',
        '__pycache__/',
        '*.pyc',
        '.pytest_cache/',
        'data/temp/'
    ]
    
    existing_content = ""
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
    
    new_entries = []
    for entry in required_entries:
        if entry not in existing_content:
            new_entries.append(entry)
    
    if new_entries:
        with gitignore_path.open('a') as f:
            if existing_content and not existing_content.endswith('\n'):
                f.write('\n')
            f.write('# Morning Digest\n')
            for entry in new_entries:
                f.write(f"{entry}\n")
        logging.info(f"Added {len(new_entries)} entries to .gitignore")
    else:
        logging.info(".gitignore is up to date")

def main():
    """Main setup function."""
    setup_logging()
    logging.info("Starting Morning Digest setup...")
    
    # Change to project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    # Create directories
    created_dirs = create_directories()
    if created_dirs:
        logging.info(f"Created {len(created_dirs)} directories")
    
    # Setup configuration files
    create_env_example()
    setup_gitignore()
    
    # Validate environment
    env_valid, missing_env = validate_environment_variables()
    if not env_valid:
        logging.warning(f"Missing environment variables: {', '.join(missing_env)}")
        logging.warning("Please create a .env file with the required variables")
    else:
        logging.info("All required environment variables are set")
    
    # Validate config files
    config_valid, missing_config = validate_config_files()
    if not config_valid:
        logging.error(f"Missing configuration files: {', '.join(missing_config)}")
        return False
    else:
        logging.info("All configuration files are present")
    
    # Check dependencies
    deps_valid, missing_deps = check_dependencies()
    if not deps_valid:
        logging.error(f"Missing Python packages: {', '.join(missing_deps)}")
        logging.error("Please install missing packages: pip install " + " ".join(missing_deps))
        return False
    else:
        logging.info("All required Python packages are installed")
    
    # Final status
    if env_valid and config_valid and deps_valid:
        logging.info("✅ Setup completed successfully!")
        logging.info("You can now run the morning digest with: python src/main.py")
        return True
    else:
        logging.error("❌ Setup completed with issues. Please resolve the above problems.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)