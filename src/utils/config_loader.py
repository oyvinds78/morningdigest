import os
import json
import yaml
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Default config files
        self.settings_file = self.config_dir / "settings.yaml"
        self.news_sources_file = self.config_dir / "news_sources.json"
        self.agent_prompts_file = self.config_dir / "agent_prompts.json"
        
        # Load configurations
        self._settings = None
        self._news_sources = None
        self._agent_prompts = None
        
        # Environment variables prefix
        self.env_prefix = "MORNING_DIGEST_"
    
    @property
    def settings(self) -> Dict[str, Any]:
        """Get application settings"""
        if self._settings is None:
            self._settings = self._load_settings()
        return self._settings
    
    @property
    def news_sources(self) -> Dict[str, Any]:
        """Get news sources configuration"""
        if self._news_sources is None:
            self._news_sources = self._load_news_sources()
        return self._news_sources
    
    @property
    def agent_prompts(self) -> Dict[str, Any]:
        """Get agent prompts configuration"""
        if self._agent_prompts is None:
            self._agent_prompts = self._load_agent_prompts()
        return self._agent_prompts
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load main application settings"""
        default_settings = self._get_default_settings()
        
        # Try to load from file
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    file_settings = yaml.safe_load(f) or {}
                
                # Merge with defaults
                merged_settings = self._deep_merge(default_settings, file_settings)
                
                # Override with environment variables
                env_settings = self._load_env_settings()
                final_settings = self._deep_merge(merged_settings, env_settings)
                
                logging.info("Settings loaded successfully")
                return final_settings
                
            except Exception as e:
                logging.error(f"Failed to load settings file: {e}")
                logging.info("Using default settings")
        
        else:
            # Create default settings file
            self._create_default_settings_file()
            logging.info("Created default settings file")
        
        # Apply environment overrides to defaults
        env_settings = self._load_env_settings()
        return self._deep_merge(default_settings, env_settings)
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """Get default application settings"""
        return {
            "general": {
                "location": "Trondheim, Norway",
                "timezone": "Europe/Oslo",
                "language": "no",
                "user_context": {
                    "family": {
                        "children_ages": [5, 7],
                        "partner_age": 39
                    },
                    "career": {
                        "current_transition": "restaurant_to_ml_ai",
                        "interests": ["python", "machine_learning", "automation", "productivity"]
                    },
                    "personal": {
                        "hobbies": ["writing", "music", "carpentry"],
                        "learning_style": "analogies_helpful",
                        "values": ["critical_thinking", "efficiency", "family_time"]
                    }
                }
            },
            "agents": {
                "max_tokens_per_agent": 1000,
                "timeout_seconds": 30,
                "retry_attempts": 2,
                "parallel_execution": True
            },
            "email": {
                "send_time": "07:30",
                "timezone": "Europe/Oslo",
                "format": "html",
                "subject_template": "Din morgenoppdatering - {date}",
                "fallback_to_text": True
            },
            "claude": {
                "model": "claude-3-5-sonnet-20241022",
                "daily_token_budget": 10000,
                "enable_usage_tracking": True,
                "rate_limit_requests_per_minute": 10
            },
            "schedule": {
                "enabled": True,
                "retry_on_failure": True,
                "max_runtime_minutes": 10,
                "timezone": "Europe/Oslo"
            },
            "data_collection": {
                "news_hours_back": 24,
                "calendar_days_ahead": 7,
                "newsletter_hours_back": 24,
                "weather_location": "Trondheim,NO",
                "medium_hours_back": 48
            },
            "features": {
                "include_weather": True,
                "include_calendar": True,
                "include_news": True,
                "include_tech": True,
                "include_newsletters": True,
                "include_medium": True
            },
            "logging": {
                "level": "INFO",
                "file_path": "logs/morning_digest.log",
                "max_file_size_mb": 10,
                "backup_count": 5
            }
        }
    
    def _load_news_sources(self) -> Dict[str, Any]:
        """Load news sources configuration"""
        if self.news_sources_file.exists():
            try:
                with open(self.news_sources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load news sources: {e}")
        
        # Return default news sources
        default_sources = {
            "norwegian_local": [
                {"name": "NRK Trøndelag", "rss": "https://www.nrk.no/trondelag/toppsaker.rss", "priority": "high"},
                {"name": "Adressa", "rss": "https://www.adressa.no/rss.xml", "priority": "high"}
            ],
            "norwegian_national": [
                {"name": "NRK Hovedsaker", "rss": "https://www.nrk.no/toppsaker.rss", "priority": "medium"},
                {"name": "VG Innenriks", "rss": "https://www.vg.no/rss/feed/?categories=1069", "priority": "medium"},
                {"name": "Aftenposten Hovedsaker", "rss": "https://www.aftenposten.no/rss/", "priority": "medium"}
            ],
            "international": [
                {"name": "BBC World", "rss": "http://feeds.bbci.co.uk/news/world/rss.xml", "priority": "medium"},
                {"name": "Al Jazeera English", "rss": "https://www.aljazeera.com/xml/rss/all.xml", "priority": "medium"}
            ],
            "international_tabloid": [
                {"name": "VG Utenriks", "rss": "https://www.vg.no/rss/feed/?categories=1070", "priority": "low"}
            ],
            "tech_sources": [
                {"name": "Kode24", "rss": "https://www.kode24.no/rss", "priority": "high"}
            ]
        }
        
        # Create default file
        try:
            with open(self.news_sources_file, 'w', encoding='utf-8') as f:
                json.dump(default_sources, f, indent=2, ensure_ascii=False)
            logging.info("Created default news sources file")
        except Exception as e:
            logging.error(f"Failed to create default news sources file: {e}")
        
        return default_sources
    
    def _load_agent_prompts(self) -> Dict[str, Any]:
        """Load agent prompts configuration"""
        if self.agent_prompts_file.exists():
            try:
                with open(self.agent_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load agent prompts: {e}")
        
        # Return default prompts (these could be overridden)
        default_prompts = {
            "norwegian_news_agent": {
                "system_prompt": "You are a Norwegian news analyst...",
                "max_tokens": 1000
            },
            "tech_intelligence_agent": {
                "system_prompt": "You are a tech industry analyst...",
                "max_tokens": 1000
            },
            "calendar_intelligence_agent": {
                "system_prompt": "You are a personal assistant...",
                "max_tokens": 800
            },
            "newsletter_intelligence_agent": {
                "system_prompt": "You are a comprehensive newsletter analyst...",
                "max_tokens": 1000
            },
            "master_coordinator_agent": {
                "system_prompt": "You are the master coordinator...",
                "max_tokens": 1200
            }
        }
        
        return default_prompts
    
    def _load_env_settings(self) -> Dict[str, Any]:
        """Load settings from environment variables"""
        env_settings = {}
        
        # Map environment variables to config structure
        env_mappings = {
            f"{self.env_prefix}CLAUDE_API_KEY": ["claude", "api_key"],
            f"{self.env_prefix}OPENWEATHER_API_KEY": ["apis", "openweather_api_key"],
            f"{self.env_prefix}GMAIL_ADDRESS": ["email", "gmail_address"],
            f"{self.env_prefix}RECIPIENT_EMAIL": ["email", "recipient_email"],
            f"{self.env_prefix}SEND_TIME": ["email", "send_time"],
            f"{self.env_prefix}LOCATION": ["general", "location"],
            f"{self.env_prefix}TOKEN_BUDGET": ["claude", "daily_token_budget"],
            f"{self.env_prefix}LOG_LEVEL": ["logging", "level"],
            f"{self.env_prefix}SCHEDULE_ENABLED": ["schedule", "enabled"],
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                converted_value = self._convert_env_value(value)
                self._set_nested_value(env_settings, config_path, converted_value)
        
        return env_settings
    
    def _convert_env_value(self, value: str) -> Union[str, int, float, bool]:
        """Convert environment variable string to appropriate type"""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value
    
    def _set_nested_value(self, dictionary: Dict, path: list, value: Any):
        """Set a value in a nested dictionary using a path"""
        for key in path[:-1]:
            if key not in dictionary:
                dictionary[key] = {}
            dictionary = dictionary[key]
        dictionary[path[-1]] = value
    
    def _deep_merge(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _create_default_settings_file(self):
        """Create default settings file"""
        try:
            default_settings = self._get_default_settings()
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_settings, f, default_flow_style=False, allow_unicode=True, indent=2)
        except Exception as e:
            logging.error(f"Failed to create default settings file: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation"""
        keys = key.split('.')
        value = self.settings
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting and save to file"""
        try:
            keys = key.split('.')
            settings = self.settings.copy()
            
            # Navigate to the parent of the target key
            current = settings
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            
            # Set the value
            current[keys[-1]] = value
            
            # Save to file
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                yaml.dump(settings, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            # Update cached settings
            self._settings = settings
            
            logging.info(f"Updated setting: {key} = {value}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to update setting {key}: {e}")
            return False
    
    def reload(self):
        """Reload all configurations from files"""
        self._settings = None
        self._news_sources = None
        self._agent_prompts = None
        logging.info("Configuration reloaded")
    
    def validate_config(self) -> Dict[str, bool]:
        """Validate configuration completeness"""
        validation_results = {
            'claude_api_key': False,
            'openweather_api_key': False,
            'email_config': False,
            'news_sources': False,
            'required_settings': False
        }
        
        # Check Claude API key
        claude_key = self.get('claude.api_key') or os.getenv('CLAUDE_API_KEY')
        validation_results['claude_api_key'] = bool(claude_key)
        
        # Check OpenWeather API key
        weather_key = self.get('apis.openweather_api_key') or os.getenv('OPENWEATHER_API_KEY')
        validation_results['openweather_api_key'] = bool(weather_key)
        
        # Check email configuration
        gmail_address = self.get('email.gmail_address') or os.getenv('GMAIL_ADDRESS')
        recipient_email = self.get('email.recipient_email') or os.getenv('RECIPIENT_EMAIL')
        validation_results['email_config'] = bool(gmail_address and recipient_email)
        
        # Check news sources
        validation_results['news_sources'] = bool(self.news_sources)
        
        # Check required settings
        required_keys = [
            'general.location',
            'email.send_time',
            'claude.model'
        ]
        
        all_required_present = all(self.get(key) is not None for key in required_keys)
        validation_results['required_settings'] = all_required_present
        
        return validation_results

# Example usage
def main():
    """Configuration validation and setup"""
    config = ConfigLoader()
    
    print("=== Morning Digest Configuration ===\n")
    
    # Validate configuration
    validation = config.validate_config()
    
    print("Configuration Status:")
    for item, is_valid in validation.items():
        status = "✓" if is_valid else "✗"
        readable_name = item.replace('_', ' ').title()
        print(f"{status} {readable_name}")
    
    if not all(validation.values()):
        print("\n⚠️  Some configuration is missing!")
        print("Please check the following:")
        
        if not validation['claude_api_key']:
            print("- Set CLAUDE_API_KEY environment variable")
        
        if not validation['openweather_api_key']:
            print("- Set OPENWEATHER_API_KEY environment variable")
        
        if not validation['email_config']:
            print("- Set GMAIL_ADDRESS and RECIPIENT_EMAIL environment variables")
        
        print(f"\nConfiguration files location: {config.config_dir}")
        print("You can also edit settings.yaml manually.")
    
    else:
        print("\n✅ All configuration is valid!")
    
    # Display some key settings
    print(f"\nKey Settings:")
    print(f"Location: {config.get('general.location')}")
    print(f"Send Time: {config.get('email.send_time')}")
    print(f"Language: {config.get('general.language')}")
    print(f"Claude Model: {config.get('claude.model')}")
    print(f"Token Budget: {config.get('claude.daily_token_budget')}")

if __name__ == "__main__":
    main()