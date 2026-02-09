#!/usr/bin/env python3
"""
Utility Functions Module
This module contains helper functions used throughout the application.
"""

# Import built-in Python modules
import json      # Used for working with JSON data
import logging   # Used for logging messages
import os        # Used for file system operations
from datetime import datetime  # Used for working with dates and times

# Set up a logger for this module
logger = logging.getLogger(__name__)


def format_error_message(error, context=""):
    """
    Format an error message with additional context.
    
    This function takes an error and makes it more readable by adding
    context about where/when the error occurred.
    
    Args:
        error (Exception): The error that occurred
        context (str): Additional information about what was happening when error occurred
        
    Returns:
        str: A formatted error message
        
    Example:
        >>> try:
        >>>     risky_operation()
        >>> except Exception as e:
        >>>     msg = format_error_message(e, "while creating index")
        >>>     print(msg)
    """
    # Get the error type and message
    # type(error).__name__ gets the class name of the error (e.g., "ValueError")
    # str(error) converts the error to a string message
    error_type = type(error).__name__
    error_message = str(error)
    
    # Build the formatted message
    # If context was provided, include it
    if context:
        # f-strings allow us to embed variables in strings using {variable}
        formatted = f"Error {context}: [{error_type}] {error_message}"
    else:
        formatted = f"Error: [{error_type}] {error_message}"
    
    # Return the formatted message
    return formatted


def load_json_file(file_path):
    """
    Load and parse a JSON file.
    
    JSON (JavaScript Object Notation) is a common format for storing data.
    This function reads a JSON file and converts it to a Python dictionary.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: The parsed JSON data as a Python dictionary
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    # Log what we're doing
    logger.debug(f"Loading JSON file: {file_path}")
    
    # Try to open and read the file
    try:
        # 'with' statement ensures the file is properly closed after reading
        # 'r' means read mode
        # 'encoding' specifies how to interpret the file's bytes as text
        with open(file_path, 'r', encoding='utf-8') as file:
            # json.load() reads the file and converts JSON to Python objects
            # (JSON objects become Python dictionaries, JSON arrays become lists, etc.)
            data = json.load(file)
        
        # Log success
        logger.debug(f"Successfully loaded JSON file: {file_path}")
        
        # Return the parsed data
        return data
        
    except FileNotFoundError:
        # The file doesn't exist
        logger.error(f"JSON file not found: {file_path}")
        # Re-raise the error so the caller knows what went wrong
        raise
        
    except json.JSONDecodeError as e:
        # The file exists but contains invalid JSON
        logger.error(f"Invalid JSON in file {file_path}: {str(e)}")
        # Re-raise the error
        raise


def save_json_file(data, file_path, indent=2):
    """
    Save data to a JSON file.
    
    This function takes a Python dictionary or list and saves it as JSON.
    
    Args:
        data (dict or list): Data to save
        file_path (str): Path where to save the file
        indent (int): Number of spaces to use for indentation (default: 2)
                     This makes the JSON file more readable
    """
    # Log what we're doing
    logger.debug(f"Saving JSON file: {file_path}")
    
    try:
        # Create the directory if it doesn't exist
        # os.path.dirname() gets the directory part of the file path
        directory = os.path.dirname(file_path)
        
        # Check if directory path is not empty (could be empty for current directory)
        if directory:
            # os.makedirs() creates the directory and any parent directories needed
            # exist_ok=True means don't raise an error if the directory already exists
            os.makedirs(directory, exist_ok=True)
        
        # Open the file for writing
        # 'w' means write mode (will overwrite if file exists)
        with open(file_path, 'w', encoding='utf-8') as file:
            # json.dump() converts Python objects to JSON and writes to file
            # indent parameter makes the output formatted nicely
            # ensure_ascii=False allows non-ASCII characters (like emojis, accents)
            json.dump(data, file, indent=indent, ensure_ascii=False)
        
        # Log success
        logger.debug(f"Successfully saved JSON file: {file_path}")
        
    except Exception as e:
        # Something went wrong while saving
        logger.error(f"Failed to save JSON file {file_path}: {str(e)}")
        # Re-raise the error
        raise


def get_timestamp():
    """
    Get the current timestamp as a formatted string.
    
    Returns:
        str: Current timestamp in ISO format (e.g., "2024-02-09T18:30:45")
        
    Example:
        >>> timestamp = get_timestamp()
        >>> print(timestamp)
        "2024-02-09T18:30:45"
    """
    # datetime.now() gets the current date and time
    # isoformat() converts it to ISO 8601 format string
    # We split at '.' to remove microseconds (the tiny fractions of seconds)
    # [0] gets the first part before the '.'
    return datetime.now().isoformat().split('.')[0]


def validate_required_fields(data, required_fields, context=""):
    """
    Validate that a dictionary contains all required fields.
    
    This is useful for checking configuration files to ensure they have
    all the necessary information.
    
    Args:
        data (dict): The dictionary to validate
        required_fields (list): List of field names that must be present
        context (str): Description of what we're validating (for error messages)
        
    Raises:
        ValueError: If any required field is missing
        
    Example:
        >>> config = {"host": "localhost", "port": 9200}
        >>> required = ["host", "port", "username"]
        >>> validate_required_fields(config, required, "Elasticsearch config")
        # Raises ValueError: Missing required fields in Elasticsearch config: username
    """
    # Find which required fields are missing
    # This is a list comprehension - a compact way to build a list
    # It checks each field and includes it in the list if it's not in data
    missing_fields = [field for field in required_fields if field not in data]
    
    # Check if any fields are missing
    # 'if missing_fields:' is True if the list is not empty
    if missing_fields:
        # Build an error message
        # ', '.join(missing_fields) creates a comma-separated string from the list
        fields_str = ', '.join(missing_fields)
        
        # Create the full error message
        if context:
            error_msg = f"Missing required fields in {context}: {fields_str}"
        else:
            error_msg = f"Missing required fields: {fields_str}"
        
        # Log the error
        logger.error(error_msg)
        
        # Raise an error to stop execution
        # ValueError is used when a value (the data) is invalid
        raise ValueError(error_msg)
    
    # If we get here, all required fields are present
    logger.debug(f"All required fields present{' in ' + context if context else ''}")


def safe_get(dictionary, key, default=None):
    """
    Safely get a value from a dictionary with a default fallback.
    
    This is similar to dictionary.get() but works with nested dictionaries.
    
    Args:
        dictionary (dict): The dictionary to search
        key (str): Key to look for (can use dot notation for nested keys like "settings.index.shards")
        default: Value to return if key is not found (default: None)
        
    Returns:
        The value if found, otherwise the default value
        
    Example:
        >>> config = {"elasticsearch": {"host": "localhost", "port": 9200}}
        >>> host = safe_get(config, "elasticsearch.host")  # Returns "localhost"
        >>> timeout = safe_get(config, "elasticsearch.timeout", 30)  # Returns 30 (default)
    """
    # Split the key by dots to handle nested paths
    # "elasticsearch.host" becomes ["elasticsearch", "host"]
    keys = key.split('.')
    
    # Start with the full dictionary
    current = dictionary
    
    # Navigate through nested dictionaries
    # Iterate through each part of the key path
    for k in keys:
        # Check if current value is a dictionary and has the key
        if isinstance(current, dict) and k in current:
            # Move deeper into the nested structure
            current = current[k]
        else:
            # Key not found at this level, return default
            return default
    
    # We found the value, return it
    return current


def is_dry_run():
    """
    Check if we're running in dry-run mode.
    
    Dry-run mode means we simulate operations without actually doing them.
    This is useful for testing and previewing changes.
    
    Returns:
        bool: True if in dry-run mode, False otherwise
    """
    # Check for the DRY_RUN environment variable
    # os.environ.get() safely retrieves an environment variable
    # We convert the value to lowercase and check if it's one of the "true" values
    dry_run_env = os.environ.get('DRY_RUN', '').lower()
    
    # Return True if the variable is set to a truthy value
    return dry_run_env in ('true', '1', 'yes', 'on')


def print_banner(message, char='='):
    """
    Print a message surrounded by a banner for visibility.
    
    This makes important messages stand out in the console output.
    
    Args:
        message (str): The message to display
        char (str): Character to use for the banner (default: '=')
        
    Example:
        >>> print_banner("Starting Elasticsearch Operations")
        ===================================
        Starting Elasticsearch Operations
        ===================================
    """
    # Calculate banner width based on message length
    # len() returns the number of characters in the string
    banner_width = len(message)
    
    # Create the banner line by repeating the character
    # char * banner_width creates a string with the character repeated
    banner = char * banner_width
    
    # Print the banner, message, and bottom banner
    # Each print() adds a newline automatically
    print(banner)
    print(message)
    print(banner)
