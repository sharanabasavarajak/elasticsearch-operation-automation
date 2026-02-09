#!/usr/bin/env python3
"""
Validators Module
This module contains validation functions for Elasticsearch configurations.
"""

# Import built-in modules
import logging     # For logging
import re          # For regular expressions (pattern matching)

# Set up logger
logger = logging.getLogger(__name__)


def validate_index_name(index_name):
    """
    Validate an Elasticsearch index name.
    
    Elasticsearch has specific rules for index names:
    - Must be lowercase
    - Cannot include: \\, /, *, ?, ", <, >, |, space, comma, #
    - Cannot start with: -, _, +
    - Cannot be . or ..
    - Must be 255 bytes or less
    
    Args:
        index_name (str): Index name to validate
        
    Returns:
        bool: True if valid, False otherwise
        
    Raises:
        ValueError: If index name is invalid
    """
    # Log what we're validating
    logger.debug(f"Validating index name: {index_name}")
    
    # Check if index_name is a string
    # isinstance() checks if a variable is of a specific type
    if not isinstance(index_name, str):
        raise ValueError("Index name must be a string")
    
    # Check minimum length
    # len() returns the number of characters
    if len(index_name) == 0:
        raise ValueError("Index name cannot be empty")
    
    # Check maximum length (255 bytes)
    # encode('utf-8') converts string to bytes
    if len(index_name.encode('utf-8')) > 255:
        raise ValueError("Index name must be 255 bytes or less")
    
    # Check if it's exactly "." or ".."
    # These are reserved names
    if index_name in ['.', '..']:
        raise ValueError("Index name cannot be '.' or '..'")
    
    # Check for invalid starting characters
    # [0] gets the first character of the string
    if index_name[0] in ['-', '_', '+']:
        raise ValueError(f"Index name cannot start with '{index_name[0]}'")
    
    # Check if lowercase
    # .islower() returns True if all letters are lowercase
    # We need to check only alpha characters, not numbers or special chars
    # any() returns True if any element in the iterable is True
    # .isalpha() returns True if character is a letter
    if any(char.isalpha() and char.isupper() for char in index_name):
        raise ValueError("Index name must be lowercase")
    
    # Check for invalid characters
    # Define the list of characters that are not allowed
    invalid_chars = ['\\', '/', '*', '?', '"', '<', '>', '|', ' ', ',', '#']
    
    # Check if any invalid character is in the index name
    for char in invalid_chars:
        # 'in' operator checks if substring exists in string
        if char in index_name:
            raise ValueError(f"Index name cannot contain '{char}'")
    
    # If we got here, the name is valid
    logger.debug(f"Index name '{index_name}' is valid")
    return True


def validate_index_settings(settings):
    """
    Validate index settings.
    
    Args:
        settings (dict): Index settings to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If settings are invalid
    """
    # Log validation
    logger.debug("Validating index settings")
    
    # Settings must be a dictionary
    if not isinstance(settings, dict):
        raise ValueError("Index settings must be a dictionary")
    
    # Check specific common settings if they exist
    # Number of shards must be positive integer
    if 'number_of_shards' in settings:
        shards = settings['number_of_shards']
        
        # Check if it's an integer
        # int is the type for whole numbers in Python
        if not isinstance(shards, int):
            raise ValueError("number_of_shards must be an integer")
        
        # Check if it's positive
        if shards <= 0:
            raise ValueError("number_of_shards must be greater than 0")
    
    # Number of replicas must be non-negative integer
    if 'number_of_replicas' in settings:
        replicas = settings['number_of_replicas']
        
        if not isinstance(replicas, int):
            raise ValueError("number_of_replicas must be an integer")
        
        # Replicas can be 0 (no replicas) but not negative
        if replicas < 0:
            raise ValueError("number_of_replicas must be 0 or greater")
    
    # Validation passed
    logger.debug("Index settings are valid")
    return True


def validate_index_mappings(mappings):
    """
    Validate index mappings.
    
    Mappings define the structure of documents in an index,
    like a schema in a traditional database.
    
    Args:
        mappings (dict): Index mappings to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If mappings are invalid
    """
    # Log validation
    logger.debug("Validating index mappings")
    
    # Mappings must be a dictionary
    if not isinstance(mappings, dict):
        raise ValueError("Index mappings must be a dictionary")
    
    # Check if 'properties' field exists (this is where field definitions go)
    if 'properties' in mappings:
        properties = mappings['properties']
        
        # Properties must be a dictionary
        if not isinstance(properties, dict):
            raise ValueError("Mappings 'properties' must be a dictionary")
        
        # Validate each field definition
        # .items() returns key-value pairs from dictionary
        for field_name, field_def in properties.items():
            # Each field definition must be a dictionary
            if not isinstance(field_def, dict):
                raise ValueError(f"Field definition for '{field_name}' must be a dictionary")
            
            # Each field should have a 'type' (though Elasticsearch allows some flexibility)
            # Common types: text, keyword, integer, long, date, boolean, etc.
            if 'type' not in field_def:
                # This is just a warning, not an error, as nested objects don't need type
                logger.warning(f"Field '{field_name}' has no 'type' specified")
    
    # Validation passed
    logger.debug("Index mappings are valid")
    return True


def validate_document(document):
    """
    Validate a document to be indexed.
    
    Args:
        document (dict): Document to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If document is invalid
    """
    # Log validation
    logger.debug("Validating document")
    
    # Document must be a dictionary
    if not isinstance(document, dict):
        raise ValueError("Document must be a dictionary")
    
    # Document should not be empty
    # len() on a dictionary returns the number of keys
    if len(document) == 0:
        logger.warning("Document is empty")
    
    # Validation passed
    logger.debug("Document is valid")
    return True


def validate_template_body(body):
    """
    Validate an index template body.
    
    Index templates automatically apply settings to matching indices.
    
    Args:
        body (dict): Template body to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If template body is invalid
    """
    # Log validation
    logger.debug("Validating index template body")
    
    # Body must be a dictionary
    if not isinstance(body, dict):
        raise ValueError("Index template body must be a dictionary")
    
    # Template must have 'index_patterns' to specify which indices it applies to
    if 'index_patterns' not in body:
        raise ValueError("Index template must have 'index_patterns'")
    
    # index_patterns should be a list of patterns
    index_patterns = body['index_patterns']
    
    # Check if it's a list
    # list is the type for arrays in Python
    if not isinstance(index_patterns, list):
        raise ValueError("'index_patterns' must be a list")
    
    # Check if the list is not empty
    if len(index_patterns) == 0:
        raise ValueError("'index_patterns' cannot be empty")
    
    # Each pattern should be a string
    # enumerate() gives us both index and value
    for i, pattern in enumerate(index_patterns):
        if not isinstance(pattern, str):
            raise ValueError(f"index_patterns[{i}] must be a string")
    
    # Validate settings if present
    if 'template' in body and 'settings' in body['template']:
        validate_index_settings(body['template']['settings'])
    
    # Validate mappings if present
    if 'template' in body and 'mappings' in body['template']:
        validate_index_mappings(body['template']['mappings'])
    
    # Validation passed
    logger.debug("Index template body is valid")
    return True
