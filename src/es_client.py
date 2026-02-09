#!/usr/bin/env python3
"""
Elasticsearch Client Wrapper Module
This module provides a wrapper around the Elasticsearch Python client
to simplify common operations like creating/updating/deleting indices,
templates, and documents.
"""

# Import the official Elasticsearch Python client library
# This library provides Python functions to interact with Elasticsearch
from elasticsearch import Elasticsearch

# Import built-in Python modules
import logging  # Used for logging messages (info, warnings, errors)
import sys      # Used for system-specific functions
import time     # Used for adding delays between retries

# Import our custom utilities module (we'll create this)
from utils import format_error_message

# Set up a logger for this module
# A logger helps us track what's happening in our code
# __name__ contains the name of the current module
logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """
    A wrapper class for Elasticsearch operations.
    
    This class makes it easier to work with Elasticsearch by providing
    simple methods for common operations.
    
    Attributes:
        es: The Elasticsearch client connection object
        max_retries: Maximum number of times to retry failed operations
        retry_delay: Number of seconds to wait between retries
    """
    
    def __init__(self, config, max_retries=3, retry_delay=2):
        """
        Initialize the Elasticsearch client with configuration.
        
        Args:
            config (dict): Dictionary containing Elasticsearch configuration
                          Must include 'host', 'port', and authentication details
            max_retries (int): How many times to retry failed operations (default: 3)
            retry_delay (int): Seconds to wait between retries (default: 2)
        """
        # Store the retry settings as instance variables
        # 'self' refers to this specific instance of the class
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Build the connection URL from the config
        # Extract host and port from the config dictionary
        host = config.get('host', 'localhost')  # Use 'localhost' if 'host' not provided
        port = config.get('port', 9200)         # Use 9200 if 'port' not provided
        scheme = config.get('scheme', 'http')    # Use 'http' if 'scheme' not provided
        
        # Log what we're about to do (informational message)
        logger.info(f"Connecting to Elasticsearch at {scheme}://{host}:{port}")
        
        # Prepare authentication settings
        # Check if we're using basic authentication (username/password)
        if 'username' in config and 'password' in config:
            # Create the Elasticsearch client with username/password authentication
            self.es = Elasticsearch(
                hosts=[f"{scheme}://{host}:{port}"],  # List of hosts to connect to
                basic_auth=(config['username'], config['password']),  # Tuple of (username, password)
                verify_certs=config.get('verify_certs', True),  # Whether to verify SSL certificates
                ca_certs=config.get('ca_certs', None),  # Path to CA certificate file
            )
        # Check if we're using API key authentication
        elif 'api_key' in config:
            # Create the Elasticsearch client with API key authentication
            self.es = Elasticsearch(
                hosts=[f"{scheme}://{host}:{port}"],
                api_key=config['api_key'],  # API key for authentication
                verify_certs=config.get('verify_certs', True),
                ca_certs=config.get('ca_certs', None),
            )
        else:
            # No authentication provided, connect without credentials
            # WARNING: This should only be used in development environments
            logger.warning("No authentication configured for Elasticsearch!")
            self.es = Elasticsearch(
                hosts=[f"{scheme}://{host}:{port}"],
                verify_certs=config.get('verify_certs', False),
            )
        
        # Test the connection by pinging Elasticsearch
        # 'if not' means "if the ping fails"
        if not self.es.ping():
            # If ping fails, raise an error to stop execution
            raise ConnectionError(f"Failed to connect to Elasticsearch at {scheme}://{host}:{port}")
        
        # Log successful connection
        logger.info("Successfully connected to Elasticsearch")
    
    def _retry_operation(self, operation, *args, **kwargs):
        """
        Retry an operation multiple times if it fails.
        
        This is a private method (indicated by the underscore prefix)
        used internally to handle retries for failed operations.
        
        Args:
            operation: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the operation if successful
            
        Raises:
            Exception: If all retry attempts fail
        """
        # Loop through retry attempts
        # range(self.max_retries) creates a sequence: 0, 1, 2, ... , max_retries-1
        for attempt in range(self.max_retries):
            try:
                # Try to execute the operation
                # *args unpacks positional arguments, **kwargs unpacks keyword arguments
                result = operation(*args, **kwargs)
                
                # If we reach this line, the operation succeeded
                return result
                
            except Exception as e:
                # An error occurred during the operation
                
                # Check if this was our last attempt
                # attempt + 1 because attempt starts at 0
                if attempt + 1 >= self.max_retries:
                    # This was the last retry, so raise the error
                    logger.error(f"Operation failed after {self.max_retries} attempts: {str(e)}")
                    raise  # Re-raise the same exception
                
                # This wasn't the last attempt, so log and retry
                logger.warning(f"Operation failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}")
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                
                # Wait before retrying
                time.sleep(self.retry_delay)
    
    def create_index(self, index_name, settings=None, mappings=None):
        """
        Create a new Elasticsearch index.
        
        An index in Elasticsearch is like a database table - it stores documents
        with a defined structure (mappings) and behavior (settings).
        
        Args:
            index_name (str): Name of the index to create
            settings (dict): Index settings (shards, replicas, etc.)
            mappings (dict): Index mappings (field types and properties)
            
        Returns:
            dict: Response from Elasticsearch
            
        Raises:
            Exception: If index creation fails
        """
        # Log what we're about to do
        logger.info(f"Creating index: {index_name}")
        
        # Build the index body (configuration)
        # Start with an empty dictionary
        body = {}
        
        # Add settings if provided
        # 'if settings:' checks if settings is not None and not empty
        if settings:
            body['settings'] = settings
        
        # Add mappings if provided
        if mappings:
            body['mappings'] = mappings
        
        # Define a function to create the index
        # This allows us to use our retry logic
        def _create():
            # Call the Elasticsearch create index API
            # **body unpacks our dictionary as keyword arguments
            return self.es.indices.create(index=index_name, body=body if body else None)
        
        # Execute the create operation with retries
        response = self._retry_operation(_create)
        
        # Log success
        logger.info(f"Successfully created index: {index_name}")
        
        # Return the response from Elasticsearch
        return response
    
    def delete_index(self, index_name):
        """
        Delete an Elasticsearch index.
        
        WARNING: This permanently deletes all data in the index!
        
        Args:
            index_name (str): Name of the index to delete
            
        Returns:
            dict: Response from Elasticsearch
        """
        # Log the deletion attempt
        logger.warning(f"Deleting index: {index_name}")
        
        # Check if the index exists before trying to delete it
        if not self.es.indices.exists(index=index_name):
            # Index doesn't exist, log a warning
            logger.warning(f"Index {index_name} does not exist, skipping deletion")
            # Return a custom response indicating no action was taken
            return {'acknowledged': True, 'status': 'index_not_found'}
        
        # Define the deletion function
        def _delete():
            return self.es.indices.delete(index=index_name)
        
        # Execute with retries
        response = self._retry_operation(_delete)
        
        # Log success
        logger.info(f"Successfully deleted index: {index_name}")
        
        return response
    
    def update_index_settings(self, index_name, settings):
        """
        Update settings for an existing index.
        
        Note: Some settings can only be changed when the index is closed.
        
        Args:
            index_name (str): Name of the index to update
            settings (dict): New settings to apply
            
        Returns:
            dict: Response from Elasticsearch
        """
        # Log the update
        logger.info(f"Updating settings for index: {index_name}")
        
        # Define the update function
        def _update():
            # Put new settings to the index
            return self.es.indices.put_settings(index=index_name, body=settings)
        
        # Execute with retries
        response = self._retry_operation(_update)
        
        logger.info(f"Successfully updated settings for index: {index_name}")
        
        return response
    
    def create_index_template(self, template_name, body):
        """
        Create an index template.
        
        Index templates automatically apply settings and mappings to new indices
        that match a specific pattern.
        
        Args:
            template_name (str): Name of the template
            body (dict): Template definition (index_patterns, settings, mappings)
            
        Returns:
            dict: Response from Elasticsearch
        """
        # Log the template creation
        logger.info(f"Creating index template: {template_name}")
        
        # Define the creation function
        def _create():
            # Use the put_index_template API (for Elasticsearch 7.8+)
            # For older versions, use put_template instead
            return self.es.indices.put_index_template(name=template_name, body=body)
        
        # Execute with retries
        response = self._retry_operation(_create)
        
        logger.info(f"Successfully created index template: {template_name}")
        
        return response
    
    def delete_index_template(self, template_name):
        """
        Delete an index template.
        
        Args:
            template_name (str): Name of the template to delete
            
        Returns:
            dict: Response from Elasticsearch
        """
        # Log the deletion
        logger.warning(f"Deleting index template: {template_name}")
        
        # Check if template exists
        if not self.es.indices.exists_index_template(name=template_name):
            logger.warning(f"Index template {template_name} does not exist, skipping deletion")
            return {'acknowledged': True, 'status': 'template_not_found'}
        
        # Define the deletion function
        def _delete():
            return self.es.indices.delete_index_template(name=template_name)
        
        # Execute with retries
        response = self._retry_operation(_delete)
        
        logger.info(f"Successfully deleted index template: {template_name}")
        
        return response
    
    def index_document(self, index_name, document, doc_id=None):
        """
        Index (create or update) a document.
        
        Args:
            index_name (str): Name of the index to store the document in
            document (dict): The document to index
            doc_id (str, optional): Document ID. If not provided, Elasticsearch generates one
            
        Returns:
            dict: Response from Elasticsearch including the document ID
        """
        # Log the indexing operation
        logger.info(f"Indexing document in index: {index_name}")
        
        # Define the indexing function
        def _index():
            # If doc_id is provided, use it; otherwise let Elasticsearch generate one
            if doc_id:
                return self.es.index(index=index_name, id=doc_id, document=document)
            else:
                return self.es.index(index=index_name, document=document)
        
        # Execute with retries
        response = self._retry_operation(_index)
        
        logger.info(f"Successfully indexed document with ID: {response['_id']}")
        
        return response
    
    def delete_document(self, index_name, doc_id):
        """
        Delete a document by ID.
        
        Args:
            index_name (str): Name of the index containing the document
            doc_id (str): ID of the document to delete
            
        Returns:
            dict: Response from Elasticsearch
        """
        # Log the deletion
        logger.info(f"Deleting document {doc_id} from index: {index_name}")
        
        # Define the deletion function
        def _delete():
            return self.es.delete(index=index_name, id=doc_id)
        
        # Execute with retries
        response = self._retry_operation(_delete)
        
        logger.info(f"Successfully deleted document {doc_id}")
        
        return response
    
    def close(self):
        """
        Close the Elasticsearch client connection.
        
        It's good practice to call this when you're done using the client
        to free up resources.
        """
        # Log the closure
        logger.info("Closing Elasticsearch connection")
        
        # Close the connection
        self.es.close()
