import logging
import os
import sys
from datetime import datetime
from functools import wraps
import time

def setup_logger(name: str = "jira_streamlit") -> logging.Logger:
    """Set up logging configuration for the application."""
    
    # Create logger
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Set level from environment or default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Create formatter
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    log_file = os.getenv("LOG_FILE")
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.info(f"File logging enabled: {log_file}")
        except Exception as e:
            logger.warning(f"Could not create file handler for {log_file}: {e}")
    
    # Log startup
    logger.info(f"Logger initialized - Level: {log_level}")
    
    return logger

def log_function_call(logger: logging.Logger, log_args: bool = False, log_result: bool = False):
    """Decorator to log function calls with optional arguments and results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            # Log function entry
            if log_args and (args or kwargs):
                # Sanitize sensitive data
                safe_args = []
                for arg in args:
                    if isinstance(arg, str) and len(arg) > 50:
                        safe_args.append(f"{arg[:47]}...")
                    else:
                        safe_args.append(str(arg))
                
                safe_kwargs = {}
                for k, v in kwargs.items():
                    if 'token' in k.lower() or 'password' in k.lower():
                        safe_kwargs[k] = "***REDACTED***"
                    elif isinstance(v, str) and len(v) > 50:
                        safe_kwargs[k] = f"{v[:47]}..."
                    else:
                        safe_kwargs[k] = v
                
                logger.info(f"Calling {func_name} with args={safe_args}, kwargs={safe_kwargs}")
            else:
                logger.info(f"Calling {func_name}")
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                if log_result:
                    # Sanitize result for logging
                    if hasattr(result, '__len__') and not isinstance(result, str):
                        logger.info(f"{func_name} completed in {execution_time:.3f}s - Result length: {len(result)}")
                    else:
                        logger.info(f"{func_name} completed in {execution_time:.3f}s - Result: {str(result)[:100]}")
                else:
                    logger.info(f"{func_name} completed in {execution_time:.3f}s")
                
                # Log slow operations
                if execution_time > 2.0:
                    logger.warning(f"SLOW OPERATION: {func_name} took {execution_time:.3f}s")
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"{func_name} failed after {execution_time:.3f}s - Error: {str(e)}", exc_info=True)
                raise
                
        return wrapper
    return decorator

def log_user_action(logger: logging.Logger, action: str, **kwargs):
    """Log user actions with context."""
    context_str = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
    session_id = get_session_id()
    logger.info(f"USER_ACTION [{session_id}] {action} - {context_str}")

def get_session_id() -> str:
    """Get a simple session identifier."""
    try:
        import streamlit as st
        if hasattr(st, 'session_state') and hasattr(st.session_state, 'session_id'):
            return st.session_state.session_id
        else:
            # Create a simple session ID based on script run ID
            import hashlib
            session_id = hashlib.md5(str(id(st)).encode()).hexdigest()[:8]
            if hasattr(st, 'session_state'):
                st.session_state.session_id = session_id
            return session_id
    except:
        return "unknown"

# Global logger instance
main_logger = setup_logger()