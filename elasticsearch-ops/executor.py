#!/usr/bin/env python3
"""
Elasticsearch Operations Executor
Simple script to execute Elasticsearch operations from .properties files
"""

# Import Python standard libraries
# These come built-in with Python, no need to install
import os           # For file and directory operations
import sys          # For system operations and exit codes
import argparse     # For parsing command-line arguments
import json         # For working with JSON data
import logging      # For logging messages
from pathlib import Path  # For easier path handling

# Import Elasticsearch library (needs to be installed)
from elasticsearch import Elasticsearch

# Set up logging so we can see what's happening
# This configures how log messages are displayed
logging.basicConfig(
    level=logging.INFO,  # Show INFO level and above (INFO, WARNING, ERROR)
    format='%(asctime)s - %(levelname)s - %(message)s',  # How to format each message
    datefmt='%Y-%m-%d %H:%M:%S'  # Date format for timestamps
)
# Create a logger for this script
logger = logging.getLogger(__name__)


def load_properties_file(filepath):
    """
    Load a .properties file and return as a dictionary.
    
    Properties files have format:
        key=value
        key2=value2
    
    Args:
        filepath (str): Path to the .properties file
        
    Returns:
        dict: Dictionary with key-value pairs from the file
    """
    # Log what we're doing
    logger.info(f"Loading properties file: {filepath}")
    
    # Create empty dictionary to store properties
    properties = {}
    
    # Open the file for reading
    # 'r' means read mode
    # 'encoding' specifies how to interpret the file's bytes as text
    with open(filepath, 'r', encoding='utf-8') as file:
        # Read the file line by line
        for line_num, line in enumerate(file, start=1):
            # Remove whitespace from beginning and end of line
            line = line.strip()
            
            # Skip empty lines and comments (lines starting with #)
            # 'continue' skips to the next iteration of the loop
            if not line or line.startswith('#'):
                continue
            
            # Split the line on the first '=' character
            # This separates key from value
            if '=' in line:
                # Find the position of the first '='
                equals_pos = line.index('=')
                # Everything before '=' is the key
                key = line[:equals_pos].strip()
                # Everything after '=' is the value
                value = line[equals_pos + 1:].strip()
                
                # Store in dictionary
                properties[key] = value
            else:
                # Line doesn't have '=', log a warning
                logger.warning(f"Skipping invalid line {line_num} in {filepath}: {line}")
    
    # Log how many properties we loaded
    logger.info(f"Loaded {len(properties)} properties from {filepath}")
    
    # Return the dictionary
    return properties


def load_environment_config(env_name, configs_dir='configs'):
    """
    Load environment configuration from .conf file.
    
    Args:
        env_name (str): Environment name (dev, qa, prod, etc.)
        configs_dir (str): Directory containing config files
        
    Returns:
        dict: Environment configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
    """
    # Build the path to the config file
    # f-string lets us embed variables: f"{variable}.conf"
    config_file = os.path.join(configs_dir, f"{env_name}.conf")
    
    # Check if file exists
    if not os.path.exists(config_file):
        # File doesn't exist, raise an error
        error_msg = f"Environment config not found: {config_file}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    # Load the config file using our properties loader
    config = load_properties_file(config_file)
    
    # Validate required fields
    # These fields must be present in every environment config
    required_fields = ['ES_HOST', 'ES_PORT', 'ES_SCHEME']
    
    # Check if all required fields are present
    # List comprehension to find missing fields
    missing = [field for field in required_fields if field not in config]
    
    if missing:
        # Some required fields are missing
        error_msg = f"Missing required fields in {config_file}: {', '.join(missing)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Return the loaded config
    return config


def connect_to_elasticsearch(env_config):
    """
    Create and test Elasticsearch connection.
    
    Args:
        env_config (dict): Environment configuration
        
    Returns:
        Elasticsearch: Connected Elasticsearch client
        
    Raises:
        ConnectionError: If unable to connect
    """
    # Extract connection details from config
    host = env_config['ES_HOST']
    port = env_config['ES_PORT']
    scheme = env_config['ES_SCHEME']
    
    # Build connection URL
    url = f"{scheme}://{host}:{port}"
    
    logger.info(f"Connecting to Elasticsearch: {url}")
    
    # Check if authentication is configured
    # .get() returns None if key doesn't exist
    username = env_config.get('ES_USERNAME')
    password = env_config.get('ES_PASSWORD')
    
    # Create Elasticsearch client
    if username and password:
        # Use basic authentication
        es = Elasticsearch(
            hosts=[url],
            basic_auth=(username, password),  # Tuple of (username, password)
            verify_certs=env_config.get('VERIFY_CERTS', 'true').lower() == 'true'
        )
    else:
        # No authentication (only for dev/test environments)
        logger.warning("No authentication configured!")
        es = Elasticsearch(
            hosts=[url],
            verify_certs=False
        )
    
    # Test the connection by pinging
    if not es.ping():
        # Ping failed, connection is not working
        raise ConnectionError(f"Failed to connect to Elasticsearch at {url}")
    
    logger.info("Successfully connected to Elasticsearch")
    
    # Return the connected client
    return es


def find_version_operations(version, versions_dir='versions'):
    """
    Find all .properties files in a version folder.
    
    Args:
        version (str): Version number or 'latest'
        versions_dir (str): Directory containing version folders
        
    Returns:
        list: List of tuples (filepath, properties_dict)
    """
    # Handle 'latest' keyword
    if version == 'latest':
        # Find the highest numbered version folder
        # List all directories in versions_dir
        version_folders = [
            d for d in os.listdir(versions_dir)
            # Check if it's a directory and the name is a number
            if os.path.isdir(os.path.join(versions_dir, d)) and d.isdigit()
        ]
        
        if not version_folders:
            # No version folders found
            raise ValueError(f"No version folders found in {versions_dir}")
        
        # Convert to integers and find the maximum
        # sorted() sorts the list, reverse=True gives descending order
        latest_version = sorted([int(v) for v in version_folders], reverse=True)[0]
        version = str(latest_version)
        logger.info(f"Using latest version: {version}")
    
    # Build path to version folder
    version_path = os.path.join(versions_dir, version)
    
    # Check if version folder exists
    if not os.path.exists(version_path):
        raise ValueError(f"Version folder not found: {version_path}")
    
    # Find all .properties files in the version folder
    # os.listdir() returns all files and folders
    properties_files = [
        f for f in os.listdir(version_path)
        # Check if it ends with .properties
        if f.endswith('.properties')
    ]
    
    if not properties_files:
        # No properties files found
        raise ValueError(f"No .properties files found in {version_path}")
    
    logger.info(f"Found {len(properties_files)} operation files in version {version}")
    
    # Load each properties file
    operations = []
    # Sort files alphabetically so they execute in predictable order
    for filename in sorted(properties_files):
        # Build full path to file
        filepath = os.path.join(version_path, filename)
        # Load the properties
        props = load_properties_file(filepath)
        # Add filename to properties for reference
        props['_filename'] = filename
        # Add to list as tuple
        operations.append((filepath, props))
    
    # Return list of operations
    return operations


def execute_operation(es, operation_props):
    """
    Execute a single Elasticsearch operation.
    
    Args:
        es (Elasticsearch): Elasticsearch client
        operation_props (dict): Operation properties from .properties file
        
    Returns:
        dict: Result from Elasticsearch
        
    Raises:
        ValueError: If operation type is unknown or required fields missing
    """
    # Get the operation type (required)
    if 'operation' not in operation_props:
        raise ValueError("Missing 'operation' field in properties file")
    
    operation = operation_props['operation']
    filename = operation_props.get('_filename', 'unknown')
    
    logger.info(f"Executing operation '{operation}' from {filename}")
    
    # Route to appropriate handler based on operation type
    
    # === CREATE INDEX ===
    if operation == 'create_index':
        # Required: indexname
        if 'indexname' not in operation_props:
            raise ValueError(f"Missing 'indexname' for create_index in {filename}")
        
        index_name = operation_props['indexname']
        
        # Build index body
        # Start with empty dict
        body = {}
        
        # Add settings if provided
        settings = {}
        if 'shards' in operation_props:
            settings['number_of_shards'] = int(operation_props['shards'])
        if 'replicas' in operation_props:
            settings['number_of_replicas'] = int(operation_props['replicas'])
        
        if settings:
            body['settings'] = settings
        
        # Add mappings from inputjson if provided
        if 'inputjson' in operation_props:
            # Parse JSON string to Python dict
            input_data = json.loads(operation_props['inputjson'])
            # Merge input_data into body
            body.update(input_data)
        
        # Execute create index
        logger.info(f"Creating index: {index_name}")
        result = es.indices.create(index=index_name, body=body if body else None)
        
        return result
    
    # === DELETE INDEX ===
    elif operation == 'delete_index':
        # Required: indexname
        if 'indexname' not in operation_props:
            raise ValueError(f"Missing 'indexname' for delete_index in {filename}")
        
        index_name = operation_props['indexname']
        
        # Check if index exists first
        if not es.indices.exists(index=index_name):
            logger.warning(f"Index {index_name} does not exist, skipping deletion")
            return {'acknowledged': True, 'status': 'index_not_found'}
        
        # Execute delete
        logger.warning(f"Deleting index: {index_name}")
        result = es.indices.delete(index=index_name)
        
        return result
    
    # === UPDATE INDEX ===
    elif operation == 'update_index':
        # Required: indexname, inputjson
        if 'indexname' not in operation_props:
            raise ValueError(f"Missing 'indexname' for update_index in {filename}")
        if 'inputjson' not in operation_props:
            raise ValueError(f"Missing 'inputjson' for update_index in {filename}")
        
        index_name = operation_props['indexname']
        settings = json.loads(operation_props['inputjson'])
        
        logger.info(f"Updating index settings: {index_name}")
        result = es.indices.put_settings(index=index_name, body=settings)
        
        return result
    
    # === CREATE TEMPLATE ===
    elif operation == 'create_template':
        # Required: templatename, inputjson
        if 'templatename' not in operation_props:
            raise ValueError(f"Missing 'templatename' for create_template in {filename}")
        if 'inputjson' not in operation_props:
            raise ValueError(f"Missing 'inputjson' for create_template in {filename}")
        
        template_name = operation_props['templatename']
        body = json.loads(operation_props['inputjson'])
        
        # Add index_patterns if provided separately
        if 'indexpattern' in operation_props and 'index_patterns' not in body:
            # Can be comma-separated patterns
            patterns = [p.strip() for p in operation_props['indexpattern'].split(',')]
            body['index_patterns'] = patterns
        
        logger.info(f"Creating index template: {template_name}")
        result = es.indices.put_index_template(name=template_name, body=body)
        
        return result
    
    # === DELETE TEMPLATE ===
    elif operation == 'delete_template':
        # Required: templatename
        if 'templatename' not in operation_props:
            raise ValueError(f"Missing 'templatename' for delete_template in {filename}")
        
        template_name = operation_props['templatename']
        
        # Check if template exists
        if not es.indices.exists_index_template(name=template_name):
            logger.warning(f"Template {template_name} does not exist, skipping deletion")
            return {'acknowledged': True, 'status': 'template_not_found'}
        
        logger.warning(f"Deleting index template: {template_name}")
        result = es.indices.delete_index_template(name=template_name)
        
        return result
    
    # === INDEX DOCUMENT ===
    elif operation == 'index_document':
        # Required: indexname, inputjson
        if 'indexname' not in operation_props:
            raise ValueError(f"Missing 'indexname' for index_document in {filename}")
        if 'inputjson' not in operation_props:
            raise ValueError(f"Missing 'inputjson' for index_document in {filename}")
        
        index_name = operation_props['indexname']
        document = json.loads(operation_props['inputjson'])
        doc_id = operation_props.get('docid')  # Optional
        
        logger.info(f"Indexing document in {index_name}")
        if doc_id:
            result = es.index(index=index_name, id=doc_id, document=document)
        else:
            result = es.index(index=index_name, document=document)
        
        return result
    
    # === UNKNOWN OPERATION ===
    else:
        raise ValueError(f"Unknown operation type: {operation}")


def main():
    """
    Main entry point of the script.
    """
    # Parse command-line arguments
    # ArgumentParser helps us handle command-line options
    parser = argparse.ArgumentParser(
        description='Execute Elasticsearch operations from properties files'
    )
    
    # Add required arguments
    parser.add_argument(
        '--environment', '-e',
        required=True,
        help='Environment name (dev, qa, uat, perf, perfdr, prod, proddr)'
    )
    
    parser.add_argument(
        '--version', '-v',
        default='latest',
        help='Version number or "latest" (default: latest)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--configs-dir',
        default='configs',
        help='Directory containing environment configs (default: configs)'
    )
    
    parser.add_argument(
        '--versions-dir',
        default='versions',
        help='Directory containing version folders (default: versions)'
    )
    
    # Parse arguments from command line
    args = parser.parse_args()
    
    # Print banner
    print("=" * 60)
    print("ELASTICSEARCH OPERATIONS EXECUTOR")
    print("=" * 60)
    print(f"Environment: {args.environment}")
    print(f"Version: {args.version}")
    print("=" * 60)
    print()
    
    try:
        # Step 1: Load environment configuration
        logger.info("Step 1: Loading environment configuration...")
        env_config = load_environment_config(args.environment, args.configs_dir)
        
        # Step 2: Connect to Elasticsearch
        logger.info("Step 2: Connecting to Elasticsearch...")
        es = connect_to_elasticsearch(env_config)
        
        # Step 3: Find operations for this version
        logger.info("Step 3: Loading operations...")
        operations = find_version_operations(args.version, args.versions_dir)
        
        # Step 4: Execute operations
        logger.info(f"Step 4: Executing {len(operations)} operations...")
        print()
        
        # Track statistics
        successful = 0
        failed = 0
        
        # Execute each operation
        for i, (filepath, operation_props) in enumerate(operations, start=1):
            # Print progress
            print(f"[{i}/{len(operations)}] {operation_props.get('_filename', 'unknown')}")
            
            try:
                # Execute the operation
                result = execute_operation(es, operation_props)
                
                # Operation succeeded
                successful += 1
                print(f"  ✓ Success")
                
            except Exception as e:
                # Operation failed
                failed += 1
                print(f"  ✗ Failed: {str(e)}")
                logger.error(f"Operation failed: {str(e)}")
                
                # Check if we should stop on error
                stop_on_error = env_config.get('STOP_ON_ERROR', 'false').lower() == 'true'
                if stop_on_error:
                    logger.error("Stopping execution due to error (STOP_ON_ERROR=true)")
                    break
        
        # Print summary
        print()
        print("=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Total operations: {len(operations)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        
        # Calculate success rate
        if len(operations) > 0:
            success_rate = (successful / len(operations)) * 100
            print(f"Success rate: {success_rate:.1f}%")
        
        print("=" * 60)
        
        # Close Elasticsearch connection
        es.close()
        
        # Return appropriate exit code
        # 0 = success, 1 = failure
        if failed > 0:
            sys.exit(1)
        else:
            sys.exit(0)
        
    except Exception as e:
        # Something went wrong
        logger.error(f"Fatal error: {str(e)}")
        print()
        print(f"ERROR: {str(e)}")
        sys.exit(1)


# This ensures main() only runs when script is executed directly
# (not when imported as a module)
if __name__ == '__main__':
    main()
