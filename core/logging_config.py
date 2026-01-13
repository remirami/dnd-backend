"""
Logging configuration for D&D Backend API

Provides structured logging with file rotation and different log levels
for various application components.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(base_dir):
    """
    Configure application logging with rotating file handlers.
    
    Creates log files in the logs/ directory with automatic rotation.
    Each log file is limited to 10MB and keeps 5 backup files.
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(base_dir) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Create handlers
    handlers = {}
    
    # General API handler
    api_handler = RotatingFileHandler(
        log_dir / 'api.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    api_handler.setFormatter(detailed_formatter)
    api_handler.setLevel(logging.INFO)
    handlers['api'] = api_handler
    
    # Combat-specific handler
    combat_handler = RotatingFileHandler(
        log_dir / 'combat.log',
        maxBytes=10485760,
        backupCount=5
    )
    combat_handler.setFormatter(detailed_formatter)
    combat_handler.setLevel(logging.INFO)
    handlers['combat'] = combat_handler
    
    # Campaign-specific handler
    campaign_handler = RotatingFileHandler(
        log_dir / 'campaign.log',
        maxBytes=10485760,
        backupCount=5
    )
    campaign_handler.setFormatter(detailed_formatter)
    campaign_handler.setLevel(logging.INFO)
    handlers['campaign'] = campaign_handler
    
    # Error handler (all errors go here)
    error_handler = RotatingFileHandler(
        log_dir / 'errors.log',
        maxBytes=10485760,
        backupCount=10  # Keep more error logs
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)
    handlers['errors'] = error_handler
    
    # Debug handler (development only)
    debug_handler = RotatingFileHandler(
        log_dir / 'debug.log',
        maxBytes=10485760,
        backupCount=3
    )
    debug_handler.setFormatter(detailed_formatter)
    debug_handler.setLevel(logging.DEBUG)
    handlers['debug'] = debug_handler
    
    return handlers


def get_logger(name):
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (e.g., 'combat', 'campaign', 'api')
    
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger(name)
