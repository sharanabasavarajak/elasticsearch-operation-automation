#!/usr/bin/env python3
"""
Elasticsearch Automation Main Script
This is the main entry point for the Elasticsearch automation tool.
It orchestrates loading configurations, validating operations, and executing them.
"""

# Import built-in Python modules
import sys       # For system operations and exit codes
import logging   # For logging  
import argparse  # For parsing command-line arguments
import os        # For environment variables and file operations

# Import our custom modules
# These are the files we created in the src directory
from config_parser import ConfigParser
from es_client import ElasticsearchClient
from validators import (
    validate_index_name,
    validate_index_settings,
    validate_index_mappings,
    validate_document,
    validate_template_body
)
from utils import (
    format_error_message,
    get_timestamp,
    is_dry_run,
    print_banner,
    safe_get,
    save_json_file
)

# Configure logging
# This sets up how log messages are displayed
# FORMAT specifies what information to include in each log message
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# DATE_FORMAT specifies how timestamps are formatted
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Configure the root logger
# basicConfig() sets up logging for the entire application
logging.basicConfig(
    level=logging.INFO,  # Minimum level of messages to log (DEBUG < INFO < WARNING < ERROR < CRITICAL)
    format=LOG_FORMAT,   # Format string defined above
    datefmt=DATE_FORMAT  # Date format defined above
)

# Create a logger for this module specifically
logger = logging.getLogger(__name__)


class ElasticsearchAutomation:
    """
    Main automation orchestrator class.
    
    This class coordinates the entire automation workflow:
    1. Load configuration
    2. Load operation definitions
    3. Validate operations
    4. Execute operations
    5. Generate reports
    """
    
    def __init__(self, environment, config_dir='./config'):
        """
        Initialize the automation orchestrator.
        
        Args:
            environment (str): Target environment (dev, qa, uat, perf, perfdr, prod, proddr)
            config_dir (str): Path to configuration directory (default: './config')
        """
        # Store parameters as instance variables
        # 'self' refers to this specific instance of the class
        self.environment = environment
        self.config_dir = config_dir
        
        # These will be set later during initialization
        self.env_config = None      # Will store environment configuration
        self.es_client = None        # Will store Elasticsearch client
        self.operations = []         # Will store list of operations to perform
        
        # Statistics for reporting
        # We'll track how many operations succeed/fail
        self.stats = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # List to store detailed results of each operation
        self.results = []
        
        # Log initialization
        logger.info(f"Initializing Elasticsearch Automation for environment: {environment}")
    
    def load_configuration(self):
        """
        Load environment configuration and operation files.
        """
        # Log what we're doing
        logger.info("Loading configuration...")
        
        # Create a ConfigParser instance
        # This object handles loading YAML configuration files
        parser = ConfigParser(self.config_dir)
        
        # Load environment-specific configuration
        # This contains Elasticsearch connection details for the target environment
        self.env_config = parser.load_environment_config(self.environment)
        
        # Load all operation definition files
        # These files define what actions to perform (create index, etc.)
        self.operations = parser.load_operation_files()
        
        # Update statistics
        # len() returns the number of items in the list
        self.stats['total'] = len(self.operations)
        
        # Log summary
        logger.info(f"Loaded {len(self.operations)} operations to perform")
        
        # Print a summary of operations
        # This makes it clear to users what will happen
        summary = parser.get_operation_summary(self.operations)
        print(summary)
    
    def connect_elasticsearch(self):
        """
        Establish connection to Elasticsearch.
        """
        # Log connection attempt
        logger.info("Connecting to Elasticsearch...")
        
        # Get the Elasticsearch configuration from environment config
        # safe_get() safely retrieves nested dictionary values
        es_config = safe_get(self.env_config, 'elasticsearch')
        
        # Check if we got the config
        if not es_config:
            # Configuration is missing, raise an error
            raise ValueError("Elasticsearch configuration not found in environment config")
        
        # Create ElasticsearchClient instance
        # This establishes the connection and tests it with a ping
        self.es_client = ElasticsearchClient(es_config)
        
        logger.info("Successfully connected to Elasticsearch")
    
    def execute_operations(self):
        """
        Execute all loaded operations.
        """
        # Print a banner to make this section visible
        print_banner("EXECUTING OPERATIONS", char='*')
        
        # Check if we're in dry-run mode
        # In dry-run mode, we simulate operations without actually doing them
        dry_run = is_dry_run()
        
        if dry_run:
            logger.warning("DRY RUN MODE: Operations will be simulated, not executed")
        
        # Loop through each operation
        # enumerate() gives us both the index (i) and the operation
        for i, operation in enumerate(self.operations):
            # Get operation details
            operation_type = operation.get('operation')
            source_file = operation.get('_file_name', 'unknown')
            
            # Log which operation we're executing
            # i+1 because i starts at 0 but we want to show "1 of 10", not "0 of 10"
            logger.info(f"Executing operation {i+1}/{len(self.operations)}: {operation_type} from {source_file}")
            
            try:
                # Execute the operation
                # This calls our internal method that routes to the appropriate handler
                if dry_run:
                    # Simulate the operation
                    result = self._simulate_operation(operation)
                else:
                    # Actually execute the operation
                    result = self._execute_operation(operation)
                
                # Operation succeeded
                self.stats['successful'] += 1  # Increment success counter ('+=' adds to existing value)
                
                # Store the result
                self.results.append({
                    'operation': operation_type,
                    'source_file': source_file,
                    'status': 'success',
                    'result': result,
                    'timestamp': get_timestamp()
                })
                
            except Exception as e:
                # Operation failed
                # Log the error
                error_msg = format_error_message(e, f"executing {operation_type}")
                logger.error(error_msg)
                
                # Update statistics
                self.stats['failed'] += 1
                
                # Store the failure result
                self.results.append({
                    'operation': operation_type,
                    'source_file': source_file,
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': get_timestamp()
                })
                
                # Check if we should stop on errors
                # Get the configuration setting (default to False if not set)
                stop_on_error = safe_get(self.env_config, 'stop_on_error', False)
                
                if stop_on_error:
                    # Stop execution immediately
                    logger.error("Stopping execution due to error (stop_on_error=true)")
                    # 'break' exits the for loop
                    break
                else:
                    # Continue with next operation
                    logger.info("Continuing with next operation...")
                    # 'continue' skips to next iteration of the loop
                    continue
    
    def _execute_operation(self, operation):
        """
        Execute a single operation.
        
        This is a private method that routes the operation to the appropriate handler.
        
        Args:
            operation (dict): Operation definition
            
        Returns:
            dict: Result from Elasticsearch
        """
        # Get the operation type
        operation_type = operation['operation']
        
        # Route to appropriate handler based on operation type
        # This uses an if-elif chain to check which operation to perform
        
        # INDEX OPERATIONS
        if operation_type == 'create_index':
            return self._create_index(operation)
        
        elif operation_type == 'delete_index':
            return self._delete_index(operation)
        
        elif operation_type == 'update_index_settings':
            return self._update_index_settings(operation)
        
        # INDEX TEMPLATE OPERATIONS
        elif operation_type == 'create_index_template':
            return self._create_index_template(operation)
        
        elif operation_type == 'delete_index_template':
            return self._delete_index_template(operation)
        
        # DOCUMENT OPERATIONS
        elif operation_type == 'index_document':
            return self._index_document(operation)
        
        elif operation_type == 'delete_document':
            return self._delete_document(operation)
        
        else:
            # Unknown operation type
            raise ValueError(f"Unknown operation type: {operation_type}")
    
    def _simulate_operation(self, operation):
        """
        Simulate an operation without actually executing it.
        
        Used in dry-run mode to preview what would happen.
        
        Args:
            operation (dict): Operation definition
            
        Returns:
            dict: Simulated result
        """
        # Get operation type
        operation_type = operation['operation']
        
        # Log the simulation
        logger.info(f"[DRY RUN] Would execute: {operation_type}")
        
        # Return a simulated successful result
        # In real execution, this would come from Elasticsearch
        return {
            'acknowledged': True,
            'dry_run': True,
            'operation': operation_type
        }
    
    # ===== INDEX OPERATION HANDLERS =====
    
    def _create_index(self, operation):
        """Handle create_index operation."""
        # Extract parameters from operation definition
        index_name = operation['index_name']
        settings = operation.get('settings', None)  # Optional
        mappings = operation.get('mappings', None)  # Optional
        
        # Validate index name
        validate_index_name(index_name)
        
        # Validate settings if provided
        if settings:
            validate_index_settings(settings)
        
        # Validate mappings if provided
        if mappings:
            validate_index_mappings(mappings)
        
        # Execute the operation
        return self.es_client.create_index(index_name, settings, mappings)
    
    def _delete_index(self, operation):
        """Handle delete_index operation."""
        # Extract index name
        index_name = operation['index_name']
        
        # Validate index name
        validate_index_name(index_name)
        
        # Execute the operation
        return self.es_client.delete_index(index_name)
    
    def _update_index_settings(self, operation):
        """Handle update_index_settings operation."""
        # Extract parameters
        index_name = operation['index_name']
        settings = operation['settings']
        
        # Validate
        validate_index_name(index_name)
        validate_index_settings(settings)
        
        # Execute
        return self.es_client.update_index_settings(index_name, settings)
    
    # ===== INDEX TEMPLATE OPERATION HANDLERS =====
    
    def _create_index_template(self, operation):
        """Handle create_index_template operation."""
        # Extract parameters
        template_name = operation['template_name']
        
        # Build template body
        # The body might already be in 'body' key, or we might need to construct it
        if 'body' in operation:
            body = operation['body']
        else:
            # Construct body from individual components
            body = {}
            
            if 'index_patterns' in operation:
                body['index_patterns'] = operation['index_patterns']
            
            # Build template section
            template_section = {}
            
            if 'settings' in operation:
                template_section['settings'] = operation['settings']
            
            if 'mappings' in operation:
                template_section['mappings'] = operation['mappings']
            
            if template_section:
                body['template'] = template_section
        
        # Validate
        validate_template_body(body)
        
        # Execute
        return self.es_client.create_index_template(template_name, body)
    
    def _delete_index_template(self, operation):
        """Handle delete_index_template operation."""
        # Extract template name
        template_name = operation['template_name']
        
        # Execute
        return self.es_client.delete_index_template(template_name)
    
    # ===== DOCUMENT OPERATION HANDLERS =====
    
    def _index_document(self, operation):
        """Handle index_document operation."""
        # Extract parameters
        index_name = operation['index_name']
        document = operation['document']
        doc_id = operation.get('doc_id', None)  # Optional
        
        # Validate
        validate_index_name(index_name)
        validate_document(document)
        
        # Execute
        return self.es_client.index_document(index_name, document, doc_id)
    
    def _delete_document(self, operation):
        """Handle delete_document operation."""
        # Extract parameters
        index_name = operation['index_name']
        doc_id = operation['doc_id']
        
        # Validate
        validate_index_name(index_name)
        
        # Execute
        return self.es_client.delete_document(index_name, doc_id)
    
    def generate_report(self, output_file=None):
        """
        Generate execution report.
        
        Args:
            output_file (str, optional): Path to save report JSON file
        """
        # Print banner
        print_banner("EXECUTION REPORT", char='=')
        
        # Print statistics
        print(f"\nEnvironment: {self.environment}")
        print(f"Timestamp: {get_timestamp()}")
        print(f"\nResults:")
        print(f"  Total operations:      {self.stats['total']}")
        print(f"  Successful:            {self.stats['successful']}")
        print(f"  Failed:                {self.stats['failed']}")
        print(f"  Skipped:               {self.stats['skipped']}")
        
        # Calculate success rate
        # Avoid division by zero
        if self.stats['total'] > 0:
            # Calculate percentage (multiply by 100 to get percentage)
            # :.2f formats the number to 2 decimal places
            success_rate = (self.stats['successful'] / self.stats['total']) * 100
            print(f"  Success rate:          {success_rate:.2f}%")
        
        # Print detailed results for failed operations
        # List comprehension to filter only failed results
        failed_results = [r for r in self.results if r['status'] == 'failed']
        
        if failed_results:
            print("\nFailed operations:")
            # Loop through failed results
            for result in failed_results:
                print(f"  - {result['operation']} from {result['source_file']}")
                print(f"    Error: {result['error']}")
        
        # Save report to file if requested
        if output_file:
            # Build report data structure
            report = {
                'environment': self.environment,
                'timestamp': get_timestamp(),
                'statistics': self.stats,
                'results': self.results
            }
            
            # Save to JSON file
            save_json_file(report, output_file)
            print(f"\nDetailed report saved to: {output_file}")
    
    def cleanup(self):
        """
        Cleanup resources.
        
        This is called at the end to close connections and free resources.
        """
        # Close Elasticsearch connection if it exists
        if self.es_client:
            self.es_client.close()
        
        logger.info("Cleanup completed")
    
    def run(self):
        """
        Run the complete automation workflow.
        
        This is the main method that orchestrates everything.
        
        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        try:
            # Step 1: Load configuration
            self.load_configuration()
            
            # Step 2: Connect to Elasticsearch
            self.connect_elasticsearch()
            
            # Step 3: Execute operations
            self.execute_operations()
            
            # Step 4: Generate report
            # Build output file path if configured
            report_file = safe_get(self.env_config, 'report_file', None)
            self.generate_report(output_file=report_file)
            
            # Step 5: Cleanup
            self.cleanup()
            
            # Determine exit code based on results
            # Exit code 0 means success, 1 means failure
            # We return 1 if any operations failed
            if self.stats['failed'] > 0:
                return 1
            else:
                return 0
            
        except Exception as e:
            # Something went wrong in the overall workflow
            error_msg = format_error_message(e, "during execution")
            logger.error(error_msg)
            
            # Try to cleanup even if there was an error
            try:
                self.cleanup()
            except:
                # Ignore cleanup errors
                # 'pass' means do nothing
                pass
            
            # Return failure exit code
            return 1


def main():
    """
    Main entry point for the script.
    
    This function is called when the script is run from the command line.
    """
    # Create argument parser
    # ArgumentParser helps parse command-line arguments like --environment dev
    parser = argparse.ArgumentParser(
        description='Elasticsearch Operations Automation Tool',
        # formatter_class makes the help text more readable
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run for dev environment
  python es_automation.py --environment dev
  
  # Run in dry-run mode
  DRY_RUN=true python es_automation.py --environment dev
  
  # Use custom config directory
  python es_automation.py --environment prod --config /path/to/config
        '''
    )
    
    # Add command-line arguments
    # required=True means this argument must be provided
    parser.add_argument(
        '--environment', '-e',
        required=True,
        choices=['dev', 'qa', 'uat', 'perf', 'perfdr', 'prod', 'proddr'],
        help='Target environment'
    )
    
    # optional argument (no 'required=True')
    parser.add_argument(
        '--config', '-c',
        default='./config',
        help='Path to configuration directory (default: ./config)'
    )
    
    # Add verbosity flag for more detailed logging
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',  # This makes it a boolean flag (present=True, absent=False)
        help='Enable verbose logging'
    )
    
    # Parse the arguments
    # This reads sys.argv (command-line arguments) and parses them
    args = parser.parse_args()
    
    # Set logging level based on verbose flag
    if args.verbose:
        # Set to DEBUG for more detailed output
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print startup banner
    print_banner("ELASTICSEARCH OPERATIONS AUTOMATION")
    print(f"Environment: {args.environment}")
    print(f"Config directory: {args.config}")
    print(f"Dry run: {is_dry_run()}")
    print()
    
    # Create automation instance
    automation = ElasticsearchAutomation(
        environment=args.environment,
        config_dir=args.config
    )
    
    # Run the automation
    exit_code = automation.run()
    
    # Exit with the appropriate code
    # This tells the shell whether the script succeeded or failed
    sys.exit(exit_code)


# This special check ensures main() is only called when the script is run directly
# (not when it's imported as a module in another script)
if __name__ == '__main__':
    main()
