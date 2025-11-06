import logging
import traceback
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from functools import wraps
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorRecord:
    timestamp: str
    component: str
    error_type: str
    message: str
    severity: ErrorSeverity
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    resolved: bool = False

class ErrorHandler:
    def __init__(self, config_loader, email_sender=None):
        self.config = config_loader
        self.email_sender = email_sender
        
        # Error storage
        self.error_log_file = Path(self.config.get('logging.file_path', 'logs/morning_digest.log')).parent / "errors.json"
        self.error_log_file.parent.mkdir(exist_ok=True)
        
        # Error tracking
        self.recent_errors: List[ErrorRecord] = []
        self.error_counts: Dict[str, int] = {}
        self.last_notification_time: Optional[datetime] = None
        
        # Configuration
        self.max_recent_errors = 100
        self.notification_cooldown_minutes = 30
        self.max_retries = 3
        
        # Load existing errors
        self._load_error_history()
        
        # Setup logging
        self._setup_error_logging()
    
    def _setup_error_logging(self):
        """Setup error-specific logging"""
        log_level = self.config.get('logging.level', 'INFO')
        
        # Create error logger
        self.logger = logging.getLogger('error_handler')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # File handler for errors
        error_log_path = self.error_log_file.parent / "error_handler.log"
        file_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        file_handler.setLevel(logging.ERROR)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
    
    def handle_error(self, 
                    component: str, 
                    error: Exception, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    context: Optional[Dict[str, Any]] = None,
                    notify: bool = True) -> ErrorRecord:
        """Handle an error and create error record"""
        
        # Create error record
        error_record = ErrorRecord(
            timestamp=datetime.now().isoformat(),
            component=component,
            error_type=type(error).__name__,
            message=str(error),
            severity=severity,
            stack_trace=traceback.format_exc(),
            context=context or {},
            retry_count=0
        )
        
        # Log the error
        self._log_error(error_record)
        
        # Store error
        self._store_error(error_record)
        
        # Send notification if needed
        if notify and self._should_notify(error_record):
            self._send_error_notification(error_record)
        
        return error_record
    
    def handle_async_error(self, 
                          component: str, 
                          error: Exception, 
                          severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                          context: Optional[Dict[str, Any]] = None) -> ErrorRecord:
        """Handle async errors"""
        
        error_record = self.handle_error(component, error, severity, context, notify=False)
        
        # Schedule async notification
        if self._should_notify(error_record):
            asyncio.create_task(self._send_async_notification(error_record))
        
        return error_record
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error to file and console"""
        
        log_message = f"[{error_record.component}] {error_record.error_type}: {error_record.message}"
        
        if error_record.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
        elif error_record.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
        elif error_record.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
        
        # Also log stack trace for medium+ severity
        if error_record.severity.value != "low" and error_record.stack_trace:
            self.logger.debug(f"Stack trace for {error_record.component}:\n{error_record.stack_trace}")
    
    def _store_error(self, error_record: ErrorRecord):
        """Store error in memory and persistent storage"""
        
        # Add to recent errors
        self.recent_errors.append(error_record)
        
        # Maintain max recent errors
        if len(self.recent_errors) > self.max_recent_errors:
            self.recent_errors = self.recent_errors[-self.max_recent_errors:]
        
        # Update error counts
        error_key = f"{error_record.component}:{error_record.error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Save to file
        self._save_error_to_file(error_record)
    
    def _save_error_to_file(self, error_record: ErrorRecord):
        """Save error to persistent file"""
        try:
            # Load existing errors
            existing_errors = []
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    existing_errors = json.load(f)
            
            # Add new error
            error_dict = asdict(error_record)
            error_dict['severity'] = error_record.severity.value
            existing_errors.append(error_dict)
            
            # Keep only last 1000 errors
            if len(existing_errors) > 1000:
                existing_errors = existing_errors[-1000:]
            
            # Save back to file
            with open(self.error_log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_errors, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.error(f"Failed to save error to file: {e}")
    
    def _load_error_history(self):
        """Load error history from file"""
        try:
            if self.error_log_file.exists():
                with open(self.error_log_file, 'r', encoding='utf-8') as f:
                    error_data = json.load(f)
                
                # Load recent errors (last 24 hours)
                cutoff_time = datetime.now() - timedelta(hours=24)
                
                for error_dict in error_data:
                    try:
                        error_time = datetime.fromisoformat(error_dict['timestamp'])
                        if error_time > cutoff_time:
                            severity = ErrorSeverity(error_dict.get('severity', 'medium'))
                            
                            error_record = ErrorRecord(
                                timestamp=error_dict['timestamp'],
                                component=error_dict['component'],
                                error_type=error_dict['error_type'],
                                message=error_dict['message'],
                                severity=severity,
                                stack_trace=error_dict.get('stack_trace'),
                                context=error_dict.get('context', {}),
                                retry_count=error_dict.get('retry_count', 0),
                                resolved=error_dict.get('resolved', False)
                            )
                            
                            self.recent_errors.append(error_record)
                            
                            # Update error counts
                            error_key = f"{error_record.component}:{error_record.error_type}"
                            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
                    
                    except Exception as e:
                        self.logger.warning(f"Failed to load error record: {e}")
                        
        except Exception as e:
            self.logger.warning(f"Failed to load error history: {e}")
    
    def _should_notify(self, error_record: ErrorRecord) -> bool:
        """Determine if error notification should be sent"""
        
        # Always notify for critical errors
        if error_record.severity == ErrorSeverity.CRITICAL:
            return True
        
        # Check cooldown period
        if self.last_notification_time:
            time_since_last = datetime.now() - self.last_notification_time
            if time_since_last.total_seconds() < (self.notification_cooldown_minutes * 60):
                return False
        
        # Notify for high severity errors
        if error_record.severity == ErrorSeverity.HIGH:
            return True
        
        # Check if this is a recurring error
        error_key = f"{error_record.component}:{error_record.error_type}"
        if self.error_counts.get(error_key, 0) >= 3:
            return True
        
        return False
    
    def _send_error_notification(self, error_record: ErrorRecord):
        """Send error notification email"""
        try:
            if not self.email_sender:
                self.logger.warning("Email sender not configured for error notifications")
                return
            
            error_details = {
                'timestamp': error_record.timestamp,
                'component': error_record.component,
                'error': f"{error_record.error_type}: {error_record.message}",
                'severity': error_record.severity.value,
                'stack_trace': error_record.stack_trace,
                'context': error_record.context,
                'recent_error_count': len(self.recent_errors)
            }
            
            success = self.email_sender.send_error_notification(error_details)
            
            if success:
                self.last_notification_time = datetime.now()
                self.logger.info("Error notification sent successfully")
            else:
                self.logger.error("Failed to send error notification")
                
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
    
    async def _send_async_notification(self, error_record: ErrorRecord):
        """Send async error notification"""
        try:
            self._send_error_notification(error_record)
        except Exception as e:
            self.logger.error(f"Async notification failed: {e}")
    
    def with_error_handling(self, 
                           component: str, 
                           severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                           retry_count: int = 0,
                           fallback_value: Any = None):
        """Decorator for automatic error handling"""
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max(1, retry_count + 1)):
                    try:
                        return func(*args, **kwargs)
                    
                    except Exception as e:
                        error_context = {
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'max_attempts': retry_count + 1,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                        
                        error_record = self.handle_error(
                            component=component,
                            error=e,
                            severity=severity,
                            context=error_context,
                            notify=(attempt == retry_count)  # Only notify on final attempt
                        )
                        
                        error_record.retry_count = attempt + 1
                        
                        # If this is the last attempt, return fallback or re-raise
                        if attempt == retry_count:
                            if fallback_value is not None:
                                self.logger.warning(f"Returning fallback value for {component}:{func.__name__}")
                                return fallback_value
                            else:
                                raise e
                        
                        # Wait before retry
                        import time
                        time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds
            
            return wrapper
        
        return decorator
    
    def with_async_error_handling(self, 
                                 component: str, 
                                 severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                                 retry_count: int = 0,
                                 fallback_value: Any = None):
        """Async decorator for automatic error handling"""
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                for attempt in range(max(1, retry_count + 1)):
                    try:
                        return await func(*args, **kwargs)
                    
                    except Exception as e:
                        error_context = {
                            'function': func.__name__,
                            'attempt': attempt + 1,
                            'max_attempts': retry_count + 1,
                            'args_count': len(args),
                            'kwargs_keys': list(kwargs.keys())
                        }
                        
                        error_record = self.handle_async_error(
                            component=component,
                            error=e,
                            severity=severity,
                            context=error_context
                        )
                        
                        error_record.retry_count = attempt + 1
                        
                        # If this is the last attempt, return fallback or re-raise
                        if attempt == retry_count:
                            if fallback_value is not None:
                                self.logger.warning(f"Returning fallback value for {component}:{func.__name__}")
                                return fallback_value
                            else:
                                raise e
                        
                        # Wait before retry
                        await asyncio.sleep(min(2 ** attempt, 10))
            
            return wrapper
        
        return decorator
    
    def get_error_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get error summary for specified time period"""
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        recent_errors = [
            error for error in self.recent_errors
            if datetime.fromisoformat(error.timestamp) > cutoff_time
        ]
        
        # Group by component
        component_errors = {}
        severity_counts = {severity.value: 0 for severity in ErrorSeverity}
        
        for error in recent_errors:
            component = error.component
            if component not in component_errors:
                component_errors[component] = {
                    'count': 0,
                    'error_types': {},
                    'latest_error': None
                }
            
            component_errors[component]['count'] += 1
            
            error_type = error.error_type
            if error_type not in component_errors[component]['error_types']:
                component_errors[component]['error_types'][error_type] = 0
            component_errors[component]['error_types'][error_type] += 1
            
            # Track latest error for each component
            if (component_errors[component]['latest_error'] is None or
                error.timestamp > component_errors[component]['latest_error']['timestamp']):
                component_errors[component]['latest_error'] = {
                    'timestamp': error.timestamp,
                    'message': error.message,
                    'severity': error.severity.value
                }
            
            # Count by severity
            severity_counts[error.severity.value] += 1
        
        return {
            'total_errors': len(recent_errors),
            'time_period_hours': hours_back,
            'severity_breakdown': severity_counts,
            'component_breakdown': component_errors,
            'most_common_errors': self._get_most_common_errors(recent_errors),
            'error_rate_per_hour': len(recent_errors) / max(hours_back, 1)
        }
    
    def _get_most_common_errors(self, errors: List[ErrorRecord], limit: int = 5) -> List[Dict[str, Any]]:
        """Get most common error types"""
        
        error_type_counts = {}
        for error in errors:
            key = f"{error.component}:{error.error_type}"
            if key not in error_type_counts:
                error_type_counts[key] = {
                    'component': error.component,
                    'error_type': error.error_type,
                    'count': 0,
                    'latest_message': error.message
                }
            error_type_counts[key]['count'] += 1
            error_type_counts[key]['latest_message'] = error.message
        
        # Sort by count and return top errors
        sorted_errors = sorted(error_type_counts.values(), key=lambda x: x['count'], reverse=True)
        return sorted_errors[:limit]
    
    def mark_error_resolved(self, component: str, error_type: str) -> bool:
        """Mark errors of a specific type as resolved"""
        try:
            resolved_count = 0
            
            for error in self.recent_errors:
                if error.component == component and error.error_type == error_type and not error.resolved:
                    error.resolved = True
                    resolved_count += 1
            
            self.logger.info(f"Marked {resolved_count} errors as resolved: {component}:{error_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to mark errors as resolved: {e}")
            return False
    
    def clear_old_errors(self, days_back: int = 7):
        """Clear errors older than specified days"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days_back)
            
            # Filter recent errors
            self.recent_errors = [
                error for error in self.recent_errors
                if datetime.fromisoformat(error.timestamp) > cutoff_time
            ]
            
            # Rebuild error counts
            self.error_counts = {}
            for error in self.recent_errors:
                error_key = f"{error.component}:{error.error_type}"
                self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            self.logger.info(f"Cleared errors older than {days_back} days")
            
        except Exception as e:
            self.logger.error(f"Failed to clear old errors: {e}")

# Example usage and decorator examples
def main():
    """Demonstrate error handling functionality"""
    from config_loader import ConfigLoader
    
    config = ConfigLoader()
    error_handler = ErrorHandler(config)
    
    print("=== Error Handler Demo ===\n")
    
    # Demonstrate basic error handling
    try:
        raise ValueError("This is a test error")
    except Exception as e:
        error_record = error_handler.handle_error(
            component="demo",
            error=e,
            severity=ErrorSeverity.MEDIUM,
            context={"test": True}
        )
        print(f"Handled error: {error_record.message}")
    
    # Demonstrate decorator usage
    @error_handler.with_error_handling(
        component="demo_function",
        severity=ErrorSeverity.LOW,
        retry_count=2,
        fallback_value="fallback_result"
    )
    def failing_function():
        raise ConnectionError("Network unavailable")
    
    result = failing_function()
    print(f"Function result: {result}")
    
    # Show error summary
    print("\nError Summary:")
    summary = error_handler.get_error_summary(hours_back=1)
    print(f"Total errors in last hour: {summary['total_errors']}")
    print(f"Severity breakdown: {summary['severity_breakdown']}")
    
    if summary['most_common_errors']:
        print("\nMost common errors:")
        for error in summary['most_common_errors']:
            print(f"- {error['component']}:{error['error_type']} ({error['count']} times)")

if __name__ == "__main__":
    main()