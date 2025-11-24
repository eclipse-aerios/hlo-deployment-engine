'''
Module to query aeriOS service for retrieving token for m2m communication.
Used when accessing CB, even when accessing it internally 
   as this is used to propagate federation requests to other Orion-LD brokers
Used also for accessing Deployment engine local allocation manager 
   for submitting final pod placements
'''
import requests
from app.utils.decorators import catch_requests_exceptions
from app.utils.log import get_app_logger
from app.config import TOKEN_URL, WG_SERVER_URL, DEV

logger = get_app_logger()


@catch_requests_exceptions
def get_m2m_cb_token():
    '''
    Get m2m token for Orion-LD queries
    '''
    url = f"{TOKEN_URL}/cb"

    # Make a GET request to the endpoint
    response = requests.get(url=url, timeout=10)

    # Raise an exception for HTTP errors
    # response.raise_for_status() # No, handled already be decorator

    # Parse the JSON response from the server
    token_data = response.json()
    token_value = token_data.get("token")

    # Return the token value if it exists, else return None
    if token_value:
        return token_value
    else:
        logger.info("Token value not found in response.")
        return None


@catch_requests_exceptions
def get_m2m_hlo_token():
    '''
    Get m2m token for HLO Local Allocation Engine queries
    '''
    url = f"{TOKEN_URL}/hlo"

    # Make a GET request to the endpoint
    response = requests.get(url=url, timeout=10)

    # Parse the JSON response from the server
    token_data = response.json()
    token_value = token_data.get("token")

    # Return the token value if it exists, else return None
    if token_value:
        return token_value
    else:
        logger.info("Token value not found in response.")
        return None


@catch_requests_exceptions
def setup_wireguard_server(service_id: str, wg_clients: list):
    '''
    Setup wireguard server in local domain
    '''
    url = f'{WG_SERVER_URL}/service-network-overlay'
    payload = {"service_id": service_id, "peers": wg_clients}
    # Make a POST request to the endpoint
    response = requests.post(url=url, json=payload, timeout=10)

    # Raise an exception for HTTP errors
    # response.raise_for_status()
    if DEV:
        logger.info("Wireguard server setup request sent. Received: %s",
                    response.json())


def allocate_subnet(service_id: str) -> str:
    """
    Calls the FastAPI `/next_subnet` endpoint to get the next allocated subnet.
    
    Returns:
        - If successful, it returns the next allocated subnet (str).
        - If an exception occurs (e.g., no more subnets available), it returns False.
    """
    url = f'{WG_SERVER_URL}/subnet'

    try:
        payload = {"service_id": service_id}
        # Make a GET request to the `/next_subnet` endpoint
        response = requests.post(url, json=payload, timeout=5)

        # Raise an error if the response status code is not 200 (OK)
        # response.raise_for_status()

        # Parse the JSON response and return the 'next_subnet' field
        data = response.json()
        assigned_subnet = data.get('assigned_subnet', False)
        if assigned_subnet:
            if DEV:
                logger.info("Subnet %s is allocated to service %s",
                            data["assigned_subnet"], data["service_id"])
        return assigned_subnet

    except requests.exceptions.HTTPError as http_err:
        # Handle HTTP error which is probably that no more subnets exist
        logger.error("HTTP error occurred: %s", http_err)


@catch_requests_exceptions
def delete_wireguard_overlay_allocation(service_id: str):
    '''
    Setup wireguard server in local domain
    '''
    url = f'{WG_SERVER_URL}/service-network-overlay'

    # Make a GET request to the endpoint
    response = requests.delete(url=url,
                               json={"service_id": service_id},
                               timeout=10)  # <==== check here

    # Raise an exception for HTTP errors
    # response.raise_for_status()

    logger.info("Wireguard server delete overlay request sent. Received: %s",
                response.json())
