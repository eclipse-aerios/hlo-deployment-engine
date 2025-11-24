'''
 Module with funcions to check or update continuum state representations
'''
from app.api_clients.cb_client import CBClient
from app.app_models.aeriOS_continuum import ServiceComponentStatusEnum as status
from app.app_models.aeriOS_continuum import ServiceActionTypeEnum
from app.utils.log import get_app_logger

logger = get_app_logger()


def check_service_exists(service_id: str, ) -> bool:
    '''
    Check if service exists
    :param  service_id: id of the service 
    :return True or False
    '''
    cb_client = CBClient()
    jsonld_params = 'format=simplified'
    service_json = cb_client.query_entity(entity_id=service_id,
                                          ngsild_params=jsonld_params)
    try:
        if service_json is not None:
            return True
    except AttributeError:
        logger.exception('Failed to check service exists')
    return False


def check_service_component_exists(service_id: str,
                                   service_component_id: str) -> bool:
    '''
    Check if service component exists
    :param  service_id: id of the service of which part is service component
    :param  service_component_id: id of the service component id
    :return True or False
    '''
    cb_client = CBClient()
    jsonld_params = 'format=simplified'
    scomponent_json = cb_client.query_entity(entity_id=service_component_id,
                                             ngsild_params=jsonld_params)
    try:
        if scomponent_json is not None and scomponent_json.get(
                'serviceComponentStatus') is not None:
            # Check for allocating, removing, migrating
            if scomponent_json.get('serviceComponentStatus') in [
                    status.RUNNING, status.REMOVING, status.MIGRATING,
                    status.OVERLOAD
            ]:
                return True
    except AttributeError:
        logger.exception('Failed to check service component exists')
    return False


def set_service_component_status(service_id, scomponent_id,
                                 scomponent_status: str):
    """
        Set the status for a service component in CB
    """
    cb_client = CBClient()
    data = {
        "serviceComponentStatus": {
            "type": "Relationship",
            "object": scomponent_status
        }
    }
    cb_client.patch_entity(entity_id=scomponent_id, upd_object=data)


def set_service_component_status_attr(service_id, scomponent_id,
                                      scomponent_status: str):
    """
        Set the status for a service component in CB
    """
    cb_client = CBClient()

    data = {'type': 'Relationship', 'value': scomponent_status}
    cb_client.patch_entity_attr(entity_id=scomponent_id,
                                attr='serviceComponentStatus',
                                upd_object=data)


def set_service_component_ie(service_id, scomponent_id, allocated_ie_id: str):
    """
        Update IE for Service Component
        Create relationship upon allocation
        Delete relationship upon deallocation
    """
    cb_client = CBClient()
    data = {
        "infrastructureElement": {
            "type": "Relationship",
            "object": allocated_ie_id
        }
    }
    cb_client.patch_entity(entity_id=scomponent_id, upd_object=data)


def set_service_component_ie_attr(service_id, scomponent_id,
                                  allocated_ie_id: str):
    """
        Update IE for Service Component
        Create relationship upon allocation
        Delete relationship upon deallocation
    """
    cb_client = CBClient()
    data = {
        "infrastructureElement": {
            "type": "Relationship",
            "object": allocated_ie_id
        }
    }
    data = {'type': 'Relationship', 'value': allocated_ie_id}
    cb_client.patch_entity_attr(entity_id=scomponent_id,
                                attr='infrastructureElement',
                                upd_object=data)


def get_service_component_status(service_component_id: str,
                                 service_id: str = ""):
    '''
    Check if service component exists
    :param  service_id: id of the service of which part is service component
    :param  service_component_id: id of the service component id
    :return ServiceComponentStatusEnum
    '''
    # FIXME: it is dangerous
    if not service_id:
        # based on the naming convention: [urn:ngsi-ld]:[Service:05]:[Component:02]
        # Being paranoid? We could do without it also...
        scomponent_id = service_component_id
        parts = scomponent_id.split(':')
        service_id = ':'.join(parts[:4])
    cb_client = CBClient()
    jsonld_params = 'format=simplified'
    scomponent_json = cb_client.query_entity(entity_id=service_component_id,
                                             ngsild_params=jsonld_params)
    try:
        if scomponent_json is not None and scomponent_json.get(
                'serviceComponentStatus') is not None:
            return scomponent_json.get('serviceComponentStatus')
    except AttributeError:
        logger.exception('Failed to get service component status')
    return None


def get_domain_url(ie_id: str) -> str:
    """
        Get (any) domain URL and public key
    """
    cb_client = CBClient()
    jsonld_params = 'attrs=domain&format=simplified'
    domain_json = cb_client.query_entity(entity_id=ie_id,
                                         ngsild_params=jsonld_params)
    if domain_json is not None:
        jsonld_params = 'attrs=publicUrl,publicKey&format=simplified'
        try:
            url_json = cb_client.query_entity(
                entity_id=domain_json.get("domain"),
                ngsild_params=jsonld_params)
            return url_json.get("publicUrl"), url_json.get("publicKey")
        except AttributeError:
            logger.exception('Failed to get domain')
    return None


def get_host_domain():
    """
    Get local domain URL and public key
    local=true in ngsi-ld returns domain tha is localy registred in Orion-ld,
    The only locally registered domain is ...local domain
    Returns:
      publicUrl and publicKey of host domain
    """
    cb_client = CBClient()
    jsonld_params = 'type=Domain&format=simplified&local=true&attrs=publicUrl,publicKey'
    domain_json = cb_client.query_entities(ngsild_params=jsonld_params)
    # We are confident about [0] because each domain has just one domain registrered locally
    if domain_json:
        return domain_json[0].get("publicUrl"), domain_json[0].get("publicKey")
    else:
        return None


def get_full_ie_spec(ie_id: str):
    """
    Return IE hostname based on IE id.
    Not the better place to do this, could be done in data-aggregator filtering,
      but now would need protobuf related things updates. TBD later!
    :input
    @param id: str, the IE id
    :output:
    IE hostname: str

    """
    client = CBClient()
    ngsi_ld_options = "local=true&format=simplified"
    response = client.query_entity_attrs(entity_id=ie_id,
                                         attrs_list=["hostname"],
                                         ngsi_ld_params=ngsi_ld_options)
    return response["hostname"]


def get_scompnent_hosting_ie(scomponent_id: str) -> str:
    """
    Retrieve the infrastructureElement associated with a given Service Component.

    Args:
        scomponent_id (str): The NGSI-LD ID of the Service Component.

    Returns:
        str: The infrastructureElement URN if found, otherwise an empty string.
    """
    client = CBClient()
    ngsi_ld_options = "format=simplified"
    response = client.query_entity_attrs(entity_id=scomponent_id,
                                         attrs_list=["infrastructureElement"],
                                         ngsi_ld_params=ngsi_ld_options)

    if isinstance(response, dict):
        return response.get("infrastructureElement", "")
    return ""


def get_ie_llo_type(ie_id: str, is_ie_local=True) -> str:
    """
    Retrieve container technology type for a given Infrastructure Element (IE).
    If we are care about local hosted IEs, set is_ie_local to True.

    Maps common container technologies to short codes:
        - "Kubernetes" → "K8s"
        - "Docker" → "docker"
        - "containerd" → "containerd"

    Args:
        ie_id (str): The NGSI-LD URN identifier of the Infrastructure Element.

    Returns:
        str: The container technology as expected from LLO API ("K8s", "docker", or raw value if unknown).
    """
    client = CBClient()
    ngsi_ld_options = "format=simplified"
    if is_ie_local:
        ngsi_ld_options = ngsi_ld_options + "&local=true"
    response = client.query_entity_attrs(entity_id=ie_id,
                                         attrs_list=["containerTechnology"],
                                         ngsi_ld_params=ngsi_ld_options)

    # Extract value safely
    tech = response.get("containerTechnology", "").strip()

    # Map known values
    mapping = {"Kubernetes": "K8s", "Docker": "docker", "containerd": "containerd"}

    return mapping.get(
        tech, tech)  # fallback: return original value if not in mapping


def get_service_action_type(service_id: str):
    """
    Get service action type used to check if we are
    deploying or destroying a deployment.

    Returns:
        Tuple[str | None, bool | None]: 
            - "DEPLOYING", "DESTROYING", or None
            - True/False for hasOverlay, or None
    """
    cb_client = CBClient()
    jsonld_params = 'attrs=actionType,hasOverlay&format=simplified'

    service_json = cb_client.query_entity(entity_id=service_id,
                                          ngsild_params=jsonld_params)

    action_type = service_json.get("actionType")
    has_overlay = service_json.get("hasOverlay")

    return action_type, has_overlay


def get_service_handler_domain_url(service_id):
    """
    Get domain who has handled the request and is the overlay provider 
    Used when destrying a servidce deployment to delete overlay registries in handler domain
    Returns:
      str: url of domain
    """
    cb_client = CBClient()
    jsonld_params = 'attrs=domainHandler&format=simplified'
    service_json = cb_client.query_entity(entity_id=service_id,
                                          ngsild_params=jsonld_params)
    domain_handler_ref = service_json.get("domainHandler", None)
    jsonld_params = 'attrs=publicUrl&format=simplified'
    domain_json = cb_client.query_entity(entity_id=domain_handler_ref,
                                         ngsild_params=jsonld_params)
    domain_handler_url = domain_json.get("publicUrl", None)
    return domain_handler_url


def service_handled(entity_id: str, action_type: str):
    """
    Set the action type deploying for service  in CB
    Used when delete API endpoint for start service 
      called for a service that is already in CB but in a stopped (finished) state
    Reset to None in Deployment Engine when delete request is handled.
    """
    cb_client = CBClient()
    # We are called on handling a deploy request
    #  so report service is handled
    data = {}
    if action_type == ServiceActionTypeEnum.DEPLOYING:
        data = {
            "actionType": {
                "type": "Property",
                "value": ServiceActionTypeEnum.DEPLOYED
            }
        }
    # We are called on handling a destroy request
    #  so report service is handled and unset hanlder domain
    elif action_type == ServiceActionTypeEnum.DESTROYING:
        data = {
            "actionType": {
                "type": "Property",
                "value": ServiceActionTypeEnum.FINISHED
            },
            "domainHandler": {
                "type": "Relationship",
                "object": ServiceActionTypeEnum.HANDLED
            }
        }
    cb_client.patch_entity(entity_id=entity_id, upd_object=data)
