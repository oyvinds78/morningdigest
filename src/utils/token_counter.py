import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
try:
    import tiktoken
except ImportError:
    tiktoken = None
    print("Warning: tiktoken not available, using fallback token counting")
import asyncio
from functools import wraps

@dataclass
class TokenUsage:
    timestamp: str
    component: str
    operation: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: str
    cost_usd: Optional[float] = None
    duration_seconds: Optional[float] = None

@dataclass
class TokenBudget:
    daily_limit: int
    hourly_limit: int
    per_request_limit: int
    current_daily_usage: int = 0
    current_hourly_usage: int = 0
    last_reset_date: Optional[str] = None
    last_reset_hour: Optional[int] = None

class TokenCounter:
    def __init__(self, config_loader):
        self.config = config_loader
        
        # Token tracking
        self.usage_log_file = Path(self.config.get('logging.file_path', 'logs/morning_digest.log')).parent / "token_usage.json"
        self.usage_log_file.parent.mkdir(exist_ok=True)
        
        # Budget management
        self.budget_file = Path(self.config.get('logging.file_path', 'logs/morning_digest.log')).parent / "token_budget.json"
        
        # Usage tracking
        self.daily_usage: List[TokenUsage] = []
        self.component_usage: Dict[str, int] = {}
        self.model_usage: Dict[str, int] = {}
        
        # Pricing (approximate costs in USD per 1K tokens)
        self.model_pricing = {
            'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},
            'claude-3-5-haiku-20241022': {'input': 0.001, 'output': 0.005},
            'claude-3-opus-20240229': {'input': 0.015, 'output': 0.075},
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-3.5-turbo': {'input': 0.0015, 'output': 0.002}
        }
        
        # Load existing data
        self.budget = self._load_budget()
        self._load_usage_history()
        
        # Setup logging
        self.logger = logging.getLogger('token_counter')
        
        # Token encoder for counting
        self.encoder = None
        self._initialize_encoder()
    
    def _initialize_encoder(self):
        """Initialize token encoder"""
        if tiktoken:
            try:
                # Use cl100k_base encoding (used by GPT-4 and Claude)
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                self.logger.warning(f"Failed to initialize tiktoken encoder: {e}")
                self.encoder = None
        else:
            self.encoder = None
    
    def count_tokens(self, text: str, model: str = "claude-3-5-sonnet-20241022") -> int:
        """Count tokens in text"""
        if not text:
            return 0
        
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                self.logger.warning(f"Token encoding failed: {e}")
        
        # Fallback estimation (roughly 4 characters per token)
        return len(text) // 4
    
    def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str) -> float:
        """Estimate cost for token usage"""
        if model not in self.model_pricing:
            self.logger.warning(f"Unknown model for pricing: {model}")
            return 0.0
        
        pricing = self.model_pricing[model]
        
        prompt_cost = (prompt_tokens / 1000) * pricing['input']
        completion_cost = (completion_tokens / 1000) * pricing['output']
        
        return prompt_cost + completion_cost
    
    def record_usage(self, 
                    component: str,
                    operation: str,
                    prompt_tokens: int,
                    completion_tokens: int,
                    model: str,
                    duration_seconds: Optional[float] = None) -> TokenUsage:
        """Record token usage"""
        
        total_tokens = prompt_tokens + completion_tokens
        cost = self.estimate_cost(prompt_tokens, completion_tokens, model)
        
        usage = TokenUsage(
            timestamp=datetime.now().isoformat(),
            component=component,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model=model,
            cost_usd=cost,
            duration_seconds=duration_seconds
        )
        
        # Store usage
        self._store_usage(usage)
        
        # Update budget tracking
        self._update_budget_usage(total_tokens)
        
        self.logger.info(f"Token usage recorded: {component}.{operation} - {total_tokens} tokens (${cost:.4f})")
        
        return usage
    
    def _store_usage(self, usage: TokenUsage):
        """Store usage in memory and file"""
        
        # Add to daily usage
        self.daily_usage.append(usage)
        
        # Update component usage
        self.component_usage[usage.component] = self.component_usage.get(usage.component, 0) + usage.total_tokens
        
        # Update model usage
        self.model_usage[usage.model] = self.model_usage.get(usage.model, 0) + usage.total_tokens
        
        # Save to file
        self._save_usage_to_file(usage)
    
    def _save_usage_to_file(self, usage: TokenUsage):
        """Save usage to persistent file"""
        try:
            # Load existing usage
            existing_usage = []
            if self.usage_log_file.exists():
                with open(self.usage_log_file, 'r', encoding='utf-8') as f:
                    existing_usage = json.load(f)
            
            # Add new usage
            existing_usage.append(asdict(usage))
            
            # Keep only last 10,000 records
            if len(existing_usage) > 10000:
                existing_usage = existing_usage[-10000:]
            
            # Save back to file
            with open(self.usage_log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_usage, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save token usage to file: {e}")
    
    def _load_usage_history(self):
        """Load recent usage history"""
        try:
            if self.usage_log_file.exists():
                with open(self.usage_log_file, 'r', encoding='utf-8') as f:
                    usage_data = json.load(f)
                
                # Load today's usage
                today = datetime.now().date()
                
                for usage_dict in usage_data:
                    try:
                        usage_time = datetime.fromisoformat(usage_dict['timestamp'])
                        if usage_time.date() == today:
                            usage = TokenUsage(**usage_dict)
                            self.daily_usage.append(usage)
                            
                            # Update component usage
                            self.component_usage[usage.component] = self.component_usage.get(usage.component, 0) + usage.total_tokens
                            
                            # Update model usage
                            self.model_usage[usage.model] = self.model_usage.get(usage.model, 0) + usage.total_tokens
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to load usage record: {e}")
                        
        except Exception as e:
            self.logger.warning(f"Failed to load usage history: {e}")
    
    def _load_budget(self) -> TokenBudget:
        """Load token budget configuration"""
        try:
            if self.budget_file.exists():
                with open(self.budget_file, 'r', encoding='utf-8') as f:
                    budget_data = json.load(f)
                    return TokenBudget(**budget_data)
        except Exception as e:
            self.logger.warning(f"Failed to load budget file: {e}")
        
        # Create default budget
        default_budget = TokenBudget(
            daily_limit=self.config.get('claude.daily_token_budget', 10000),
            hourly_limit=self.config.get('claude.hourly_token_limit', 2000),
            per_request_limit=self.config.get('claude.per_request_token_limit', 1000),
            current_daily_usage=0,
            current_hourly_usage=0,
            last_reset_date=datetime.now().date().isoformat(),
            last_reset_hour=datetime.now().hour
        )
        
        self._save_budget(default_budget)
        return default_budget
    
    def _save_budget(self, budget: TokenBudget):
        """Save budget to file"""
        try:
            with open(self.budget_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(budget), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save budget: {e}")
    
    def _update_budget_usage(self, tokens: int):
        """Update budget usage tracking"""
        now = datetime.now()
        today = now.date().isoformat()
        current_hour = now.hour
        
        # Reset daily usage if new day
        if self.budget.last_reset_date != today:
            self.budget.current_daily_usage = 0
            self.budget.last_reset_date = today
        
        # Reset hourly usage if new hour
        if self.budget.last_reset_hour != current_hour:
            self.budget.current_hourly_usage = 0
            self.budget.last_reset_hour = current_hour
        
        # Add tokens to usage
        self.budget.current_daily_usage += tokens
        self.budget.current_hourly_usage += tokens
        
        # Save updated budget
        self._save_budget(self.budget)
    
    def check_budget(self, requested_tokens: int) -> Tuple[bool, str]:
        """Check if requested tokens are within budget"""
        
        # Check per-request limit
        if requested_tokens > self.budget.per_request_limit:
            return False, f"Request exceeds per-request limit ({requested_tokens} > {self.budget.per_request_limit})"
        
        # Check daily limit
        if self.budget.current_daily_usage + requested_tokens > self.budget.daily_limit:
            remaining = self.budget.daily_limit - self.budget.current_daily_usage
            return False, f"Request would exceed daily limit (remaining: {remaining}, requested: {requested_tokens})"
        
        # Check hourly limit
        if self.budget.current_hourly_usage + requested_tokens > self.budget.hourly_limit:
            remaining = self.budget.hourly_limit - self.budget.current_hourly_usage
            return False, f"Request would exceed hourly limit (remaining: {remaining}, requested: {requested_tokens})"
        
        return True, "Within budget"
    
    def get_usage_summary(self, days_back: int = 1) -> Dict[str, Any]:
        """Get usage summary for specified period"""
        
        cutoff_time = datetime.now() - timedelta(days=days_back)
        
        # Filter usage records
        relevant_usage = []
        if self.usage_log_file.exists():
            try:
                with open(self.usage_log_file, 'r', encoding='utf-8') as f:
                    all_usage = json.load(f)
                
                for usage_dict in all_usage:
                    try:
                        usage_time = datetime.fromisoformat(usage_dict['timestamp'])
                        if usage_time > cutoff_time:
                            relevant_usage.append(TokenUsage(**usage_dict))
                    except Exception:
                        continue
                        
            except Exception as e:
                self.logger.error(f"Failed to load usage for summary: {e}")
        
        # Calculate statistics
        total_tokens = sum(usage.total_tokens for usage in relevant_usage)
        total_cost = sum(usage.cost_usd or 0 for usage in relevant_usage)
        
        # Group by component
        component_stats = {}
        for usage in relevant_usage:
            if usage.component not in component_stats:
                component_stats[usage.component] = {
                    'total_tokens': 0,
                    'total_cost': 0,
                    'request_count': 0,
                    'avg_tokens_per_request': 0
                }
            
            component_stats[usage.component]['total_tokens'] += usage.total_tokens
            component_stats[usage.component]['total_cost'] += usage.cost_usd or 0
            component_stats[usage.component]['request_count'] += 1
        
        # Calculate averages
        for component, stats in component_stats.items():
            if stats['request_count'] > 0:
                stats['avg_tokens_per_request'] = stats['total_tokens'] / stats['request_count']
        
        # Group by model
        model_stats = {}
        for usage in relevant_usage:
            if usage.model not in model_stats:
                model_stats[usage.model] = {
                    'total_tokens': 0,
                    'total_cost': 0,
                    'request_count': 0
                }
            
            model_stats[usage.model]['total_tokens'] += usage.total_tokens
            model_stats[usage.model]['total_cost'] += usage.cost_usd or 0
            model_stats[usage.model]['request_count'] += 1
        
        return {
            'period_days': days_back,
            'total_tokens': total_tokens,
            'total_cost_usd': total_cost,
            'total_requests': len(relevant_usage),
            'avg_tokens_per_request': total_tokens / len(relevant_usage) if relevant_usage else 0,
            'component_breakdown': component_stats,
            'model_breakdown': model_stats,
            'budget_status': {
                'daily_used': self.budget.current_daily_usage,
                'daily_limit': self.budget.daily_limit,
                'daily_remaining': self.budget.daily_limit - self.budget.current_daily_usage,
                'hourly_used': self.budget.current_hourly_usage,
                'hourly_limit': self.budget.hourly_limit,
                'hourly_remaining': self.budget.hourly_limit - self.budget.current_hourly_usage
            }
        }
    
    def with_token_tracking(self, component: str, operation: str, model: str = "claude-3-5-sonnet-20241022"):
        """Decorator for automatic token tracking"""
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = datetime.now()
                
                # Extract prompt from kwargs if available
                prompt = kwargs.get('prompt', '') or (args[0] if args else '')
                prompt_tokens = self.count_tokens(str(prompt), model)
                
                # Check budget before making request
                can_proceed, budget_message = self.check_budget(prompt_tokens)
                if not can_proceed:
                    self.logger.error(f"Token budget exceeded: {budget_message}")
                    raise RuntimeError(f"Token budget exceeded: {budget_message}")
                
                try:
                    # Call the function
                    result = func(*args, **kwargs)
                    
                    # Estimate completion tokens from result
                    completion_tokens = 0
                    if isinstance(result, str):
                        completion_tokens = self.count_tokens(result, model)
                    elif isinstance(result, dict) and 'content' in result:
                        completion_tokens = self.count_tokens(str(result['content']), model)
                    
                    # Calculate duration
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    # Record usage
                    self.record_usage(
                        component=component,
                        operation=operation,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        model=model,
                        duration_seconds=duration
                    )
                    
                    return result
                    
                except Exception as e:
                    # Still record the prompt tokens even if the request failed
                    duration = (datetime.now() - start_time).total_seconds()
                    self.record_usage(
                        component=component,
                        operation=f"{operation}_failed",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=0,
                        model=model,
                        duration_seconds=duration
                    )
                    raise e
            
            return wrapper
        
        return decorator
    
    def with_async_token_tracking(self, component: str, operation: str, model: str = "claude-3-5-sonnet-20241022"):
        """Async decorator for automatic token tracking"""
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = datetime.now()
                
                # Extract prompt from kwargs if available
                prompt = kwargs.get('prompt', '') or (args[0] if args else '')
                prompt_tokens = self.count_tokens(str(prompt), model)
                
                # Check budget before making request
                can_proceed, budget_message = self.check_budget(prompt_tokens)
                if not can_proceed:
                    self.logger.error(f"Token budget exceeded: {budget_message}")
                    raise RuntimeError(f"Token budget exceeded: {budget_message}")
                
                try:
                    # Call the async function
                    result = await func(*args, **kwargs)
                    
                    # Estimate completion tokens from result
                    completion_tokens = 0
                    if isinstance(result, str):
                        completion_tokens = self.count_tokens(result, model)
                    elif isinstance(result, dict) and 'content' in result:
                        completion_tokens = self.count_tokens(str(result['content']), model)
                    
                    # Calculate duration
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    # Record usage
                    self.record_usage(
                        component=component,
                        operation=operation,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        model=model,
                        duration_seconds=duration
                    )
                    
                    return result
                    
                except Exception as e:
                    # Still record the prompt tokens even if the request failed
                    duration = (datetime.now() - start_time).total_seconds()
                    self.record_usage(
                        component=component,
                        operation=f"{operation}_failed",
                        prompt_tokens=prompt_tokens,
                        completion_tokens=0,
                        model=model,
                        duration_seconds=duration
                    )
                    raise e
            
            return wrapper
        
        return decorator
    
    def reset_daily_budget(self):
        """Manually reset daily budget"""
        self.budget.current_daily_usage = 0
        self.budget.last_reset_date = datetime.now().date().isoformat()
        self._save_budget(self.budget)
        self.logger.info("Daily token budget reset")
    
    def set_budget_limits(self, daily_limit: Optional[int] = None, 
                         hourly_limit: Optional[int] = None,
                         per_request_limit: Optional[int] = None):
        """Update budget limits"""
        if daily_limit is not None:
            self.budget.daily_limit = daily_limit
        
        if hourly_limit is not None:
            self.budget.hourly_limit = hourly_limit
        
        if per_request_limit is not None:
            self.budget.per_request_limit = per_request_limit
        
        self._save_budget(self.budget)
        self.logger.info(f"Updated budget limits: daily={self.budget.daily_limit}, hourly={self.budget.hourly_limit}, per_request={self.budget.per_request_limit}")

# Example usage
def main():
    """Demonstrate token tracking functionality"""
    from config_loader import ConfigLoader
    
    config = ConfigLoader()
    token_counter = TokenCounter(config)
    
    print("=== Token Counter Demo ===\n")
    
    # Demonstrate manual token recording
    usage = token_counter.record_usage(
        component="demo",
        operation="test_request",
        prompt_tokens=100,
        completion_tokens=50,
        model="claude-3-5-sonnet-20241022",
        duration_seconds=2.5
    )
    
    print(f"Recorded usage: {usage.total_tokens} tokens (${usage.cost_usd:.4f})")
    
    # Demonstrate decorator usage
    @token_counter.with_token_tracking(
        component="demo_function",
        operation="process_text"
    )
    def process_text(text: str) -> str:
        return f"Processed: {text}"
    
    # Check budget status
    can_proceed, message = token_counter.check_budget(500)
    print(f"\nBudget check: {can_proceed} - {message}")
    
    # Get usage summary
    summary = token_counter.get_usage_summary(days_back=1)
    print(f"\nUsage Summary:")
    print(f"Total tokens today: {summary['total_tokens']}")
    print(f"Total cost today: ${summary['total_cost_usd']:.4f}")
    print(f"Daily budget remaining: {summary['budget_status']['daily_remaining']} tokens")
    
    # Component breakdown
    if summary['component_breakdown']:
        print("\nComponent breakdown:")
        for component, stats in summary['component_breakdown'].items():
            print(f"- {component}: {stats['total_tokens']} tokens (${stats['total_cost']:.4f})")

if __name__ == "__main__":
    main()