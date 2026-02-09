#!/usr/bin/env python3
"""
Configuration Parser Module
This module handles loading and parsing configuration files for Elasticsearch operations.
"""

# Import built-in Python modules
import os        # For file path operations
import logging   # For logging
import yaml      # For parsing YAML files (you'll need to install this: pip install pyyaml)
import glob      # For finding files matching a pattern

# Import our custom modules
from utils import validate_required_fields, safe_get

# Set up logger for this module
logger = logging.getLogger(__name__)


class ConfigParser:
    """
    Parser for Elasticsearch operation configuration files.
    
    This class handles loading environment configurations and operation
    definitions from YAML files.
    """
    
    def __init__(self, config_dir):
        """
        Initialize the configuration parser.
        
        Args:
            config_dir (str): Path to the root configuration directory
        """
        # Store the config directory path as an instance variable
        self.config_dir = config_dir
        
        # Build paths to sub-directories
        # os.path.join() safely combines path parts using the correct separator for the OS
        self.environments_dir = os.path.join(config_dir, 'environments')
        self.operations_dir = os.path.join(config_dir, 'operations')
        
        # Log initialization
        logger.info(f"Initialized ConfigParser with config directory: {config_dir}")
    
    def load_environment_config(self, environment):
        """
        Load configuration for a specific environment.
        
        Args:
            environment (str): Environment name (dev, qa, prod, etc.)
            
        Returns:
            dict: Environment configuration
            
        Raises:
            FileNotFoundError: If environment config file doesn't exist
            ValueError: If required fields are missing
        """
        # Build the path to the environment config file
        # f-string embeds the environment variable in the filename
        config_file = os.path.join(self.environments_dir, f"{environment}.yml")
        
        # Log what we're doing
        logger.info(f"Loading environment config for: {environment}")
        
        # Check if the file exists
        # os.path.exists() returns True if the path exists
        if not os.path.exists(config_file):
            # File doesn't exist, raise an error
            error_msg = f"Environment config file not found: {config_file}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        # Load the YAML file
        # YAML is a human-readable data format similar to JSON
        with open(config_file, 'r', encoding='utf-8') as file:
            # yaml.safe_load() parses YAML and converts it to Python objects
            # 'safe' means it only loads standard data types (not custom Python objects)
            config = yaml.safe_load(file)
        
        # Validate that required fields are present
        # Every environment config must have these fields
        required_fields = ['elasticsearch']
        validate_required_fields(config, required_fields, f"{environment} environment config")
        
        # Validate Elasticsearch configuration
        # safe_get() safely retrieves nested dictionary values
        es_config = safe_get(config, 'elasticsearch', {})
        es_required = ['host', 'port']
        validate_required_fields(es_config, es_required, "Elasticsearch configuration")
        
        # Log success
        logger.info(f"Successfully loaded config for environment: {environment}")
        
        # Return the loaded configuration
        return config
    
    def load_operation_files(self, operation_type=None):
        """
        Load all operation definition files.
        
        Operation files define what actions to perform in Elasticsearch
        (create index, delete template, etc.)
        
        Args:
            operation_type (str, optional): Filter by operation type (indices, index_templates, documents)
                                           If None, loads all operations
            
        Returns:
            list: List of dictionaries, each containing operation definition and metadata
        """
        # Log what we're doing
        logger.info(f"Loading operation files{' for type: ' + operation_type if operation_type else ''}")
        
        # Build the search path
        # If operation_type is specified, only search that subdirectory
        if operation_type:
            search_dir = os.path.join(self.operations_dir, operation_type)
        else:
            # Search all subdirectories
            search_dir = self.operations_dir
        
        # Find all YAML files recursively
        # glob.glob() finds files matching a pattern
        # '**/*.yml' means: any subdirectory (**), any filename (*)  with .yml extension
        # recursive=True allows ** to match multiple directory levels
        pattern = os.path.join(search_dir, '**', '*.yml')
        operation_files = glob.glob(pattern, recursive=True)
        
        # Also search for .yaml extension (some people use .yaml instead of .yml)
        pattern_yaml = os.path.join(search_dir, '**', '*.yaml')
        operation_files.extend(glob.glob(pattern_yaml, recursive=True))
        
        # Log how many files we found
        logger.info(f"Found {len(operation_files)} operation files")
        
        # List to store loaded operations
        # We'll append each operation to this list
        operations = []
        
        # Loop through each file and load it
        # enumerate() gives us both the index (i) and the value (file_path)
        for i, file_path in enumerate(operation_files):
            try:
                # Log which file we're loading
                logger.debug(f"Loading operation file ({i+1}/{len(operation_files)}): {file_path}")
                
                # Open and parse the YAML file
                with open(file_path, 'r', encoding='utf-8') as file:
                    operation_data = yaml.safe_load(file)
                
                # Add metadata about the file
                # This helps with debugging and logging later
                operation_data['_source_file'] = file_path
                operation_data['_file_name'] = os.path.basename(file_path)
                
                # Validate the operation definition
                self._validate_operation(operation_data, file_path)
                
                # Add to our list
                operations.append(operation_data)
                
            except Exception as e:
                # Something went wrong loading this file
                # Log the error but continue with other files
                logger.error(f"Failed to load operation file {file_path}: {str(e)}")
                # 'continue' skips to the next iteration of the loop
                continue
        
        # Log summary
        logger.info(f"Successfully loaded {len(operations)} operation files")
        
        # Return the list of operations
        return operations
    
    def _validate_operation(self, operation_data, file_path):
        """
        Validate an operation definition.
        
        This is a private method (indicated by underscore prefix) used internally.
        
        Args:
            operation_data (dict): The operation definition to validate
            file_path (str): Path to the file (for error messages)
            
        Raises:
            ValueError: If operation definition is invalid
        """
        # Every operation must have an 'operation' field specifying what to do
        if 'operation' not in operation_data:
            error_msg = f"Missing 'operation' field in {file_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Get the operation type
        operation = operation_data['operation']
        
        # Validate based on operation type
        # Different operations require different fields
        
        # INDEX OPERATIONS
        if operation in ['create_index', 'delete_index', 'update_index_settings']:
            # These operations require an index_name
            if 'index_name' not in operation_data:
                error_msg = f"Missing 'index_name' for {operation} in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # INDEX TEMPLATE OPERATIONS
        elif operation in ['create_index_template', 'delete_index_template']:
            # These operations require a template_name
            if 'template_name' not in operation_data:
                error_msg = f"Missing 'template_name' for {operation} in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        # DOCUMENT OPERATIONS
        elif operation in ['index_document', 'delete_document']:
            # These operations require index_name
            if 'index_name' not in operation_data:
                error_msg = f"Missing 'index_name' for {operation} in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # index_document requires a document
            if operation == 'index_document' and 'document' not in operation_data:
                error_msg = f"Missing 'document' for {operation} in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # delete_document requires a doc_id
            if operation == 'delete_document' and 'doc_id' not in operation_data:
                error_msg = f"Missing 'doc_id' for {operation} in {file_path}"
                logger.error(error_msg)
                raise ValueError(error_msg)
        
        else:
            # Unknown operation type
            logger.warning(f"Unknown operation type '{operation}' in {file_path}")
        
        # Log successful validation
        logger.debug(f"Validated operation '{operation}' from {file_path}")
    
    def get_operation_summary(self, operations):
        """
        Generate a summary of operations to be performed.
        
        This creates a human-readable overview of what will be done.
        
        Args:
            operations (list): List of operation definitions
            
        Returns:
            str: Formatted summary string
        """
        # Count operations by type
        # We'll use a dictionary to count each operation type
        # We use .get() with default value 0 for operations not yet in the dict
        counts = {}
        for op in operations:
            # Get the operation type
            operation_type = op.get('operation', 'unknown')
            
            # Increment the count for this operation type
            # counts.get(operation_type, 0) returns current count or 0 if not present
            counts[operation_type] = counts.get(operation_type, 0) + 1
        
        # Build summary string
        # Start with a header
        summary = "\nOperation Summary:\n"
        summary += "=" * 50 + "\n"
        
        # Add each operation type and its count
        # .items() returns key-value pairs from the dictionary
        for operation_type, count in counts.items():
            # :30 means left-align in a field of 30 characters
            summary += f"  {operation_type:30} {count}\n"
        
        # Add total
        summary += "=" * 50 + "\n"
        summary += f"  {'Total operations:':30} {len(operations)}\n"
        
        return summary
