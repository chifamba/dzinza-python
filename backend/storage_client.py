import boto3
from botocore.exceptions import ClientError
import structlog

# Assuming your config is accessible like this
# Adjust if your project structure is different
from config import config 

logger = structlog.get_logger(__name__)

_storage_client = None

def get_storage_client():
    """
    Initializes and returns a Boto3 S3 client based on application configuration.
    Caches the client instance for reuse.
    """
    global _storage_client
    if _storage_client:
        return _storage_client

    logger.info(
        "Initializing S3 client",
        endpoint_url=config.OBJECT_STORAGE_ENDPOINT_URL,
        bucket_name=config.OBJECT_STORAGE_BUCKET_NAME,
        storage_type=config.OBJECT_STORAGE_TYPE,
        secure_mode=config.OBJECT_STORAGE_SECURE
    )
    
    try:
        client_params = {
            'service_name': 's3',
            'aws_access_key_id': config.OBJECT_STORAGE_ACCESS_KEY,
            'aws_secret_access_key': config.OBJECT_STORAGE_SECRET_KEY,
            'use_ssl': config.OBJECT_STORAGE_SECURE,
        }
        # endpoint_url is only needed for S3 compatible services like MinIO
        # For AWS S3, it should not be set, or Boto3 will try to use it and fail if it's not a valid AWS endpoint.
        if config.OBJECT_STORAGE_TYPE.lower() != 's3':
            client_params['endpoint_url'] = config.OBJECT_STORAGE_ENDPOINT_URL
        
        # Default region if not specified, important for AWS S3, less so for MinIO
        # Some S3-compatible services might still require a region.
        if 'region_name' not in client_params and config.OBJECT_STORAGE_TYPE.lower() == 's3':
             client_params['region_name'] = 'us-east-1' # Or get from config if available


        _storage_client = boto3.client(**client_params)
        logger.info("S3 client initialized successfully.")
        
        # Optional: Create bucket on first client initialization
        # create_bucket_if_not_exists(_storage_client, config.OBJECT_STORAGE_BUCKET_NAME)

    except Exception as e:
        logger.error("Failed to initialize S3 client", error=str(e), exc_info=True)
        # Depending on application requirements, you might want to raise the error
        # or handle it gracefully (e.g., by disabling features that need S3)
        _storage_client = None # Ensure client is None if initialization failed
        raise  # Re-raise the exception to make it clear initialization failed

    return _storage_client

def create_bucket_if_not_exists(client, bucket_name: str):
    """
    Checks if an S3 bucket exists, and creates it if it does not.
    Logs errors appropriately.
    """
    if not client:
        logger.error("S3 client not available, cannot create bucket.")
        return False

    try:
        # Check if bucket exists. head_bucket throws an exception if it doesn't exist or no access.
        client.head_bucket(Bucket=bucket_name)
        logger.info(f"Bucket '{bucket_name}' already exists.")
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == '404' or error_code == 'NoSuchBucket': # Not found
            logger.info(f"Bucket '{bucket_name}' not found. Attempting to create.")
            try:
                # For MinIO, location constraint is often not needed or can cause issues if not matching server config.
                # For AWS S3, you might specify LocationConstraint matching the client's region,
                # unless it's us-east-1 (which has no LocationConstraint).
                if config.OBJECT_STORAGE_TYPE.lower() == 's3' and client.meta.region_name != 'us-east-1':
                    client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': client.meta.region_name}
                    )
                else: # For MinIO or S3 us-east-1
                    client.create_bucket(Bucket=bucket_name)
                
                logger.info(f"Bucket '{bucket_name}' created successfully.")
                return True
            except ClientError as ce:
                logger.error(f"Failed to create bucket '{bucket_name}'", error=str(ce), exc_info=True)
                return False
        elif error_code == '403': # Forbidden
            logger.error(f"Access denied. Cannot check or create bucket '{bucket_name}'. Check credentials and permissions.", error=str(e))
            return False
        else: # Other errors
            logger.error(f"Error checking for bucket '{bucket_name}'", error=str(e), exc_info=True)
            return False
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred while checking/creating bucket '{bucket_name}'", error=str(e), exc_info=True)
        return False

# Example of how it might be called during app startup (conceptual)
# def initialize_storage():
#     s3_client = get_storage_client()
#     if s3_client:
#         create_bucket_if_not_exists(s3_client, config.OBJECT_STORAGE_BUCKET_NAME)

if __name__ == '__main__':
    # This is for basic testing/demonstration if run directly
    # In a real app, get_storage_client would be called by services that need it.
    # And initialize_storage (or similar) might be called from main.py
    
    # Note: For this to run, environment variables for storage config must be set,
    # or they must have defaults in config.py that allow connection.
    logger.info("Attempting to get storage client (run as script)...")
    try:
        client = get_storage_client()
        if client:
            logger.info("Successfully got storage client.")
            bucket_name_to_test = config.OBJECT_STORAGE_BUCKET_NAME
            logger.info(f"Attempting to create bucket '{bucket_name_to_test}' if not exists...")
            if create_bucket_if_not_exists(client, bucket_name_to_test):
                logger.info(f"Bucket '{bucket_name_to_test}' is ready or was created.")
            else:
                logger.error(f"Failed to ensure bucket '{bucket_name_to_test}' exists.")
        else:
            logger.error("Failed to get storage client.")
    except Exception as e:
        logger.error("Error during __main__ test run", error=str(e))
