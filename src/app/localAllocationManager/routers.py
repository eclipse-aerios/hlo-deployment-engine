'''
  Local Allocation Manager. 
  LCM of locally deployed service components. 
  Create YAML CR and submit to LLO REST API.
  Exposes aeriOS REST API for local service component allocation.
  aeriOS OpenAPI: https://aeriOS-public.pages.aeriOS-project.eu/openapis/#/hlo_al
'''
import threading
import yaml
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse
from app.api_clients import k8s_shim_client
from app.localAllocationManager.models import ServiceComponentAllocation, \
    ServiceComponentParameters, ServiceComponentNotAllocated
from app.utils import continuum_utils as manager_utils
from app.api_clients.llo_api_client import LLORESTClient
from app.utils.log import get_app_logger
from app.loop import run
from app.config import DEV
from app.localAllocationManager import crdGenarator
import app.localAllocationManager.models as LAModels
import app.app_models.aeriOS_continuum as aeriOS_c

logger = get_app_logger()

m2m_hlo_token = k8s_shim_client.get_m2m_hlo_token()


async def kafka_loop():
    '''
    New thread for the kafka consumer
    '''
    thread = threading.Thread(target=run, args=())
    thread.daemon = True  # Optional: makes the thread terminate when the main process does
    thread.start()


router = APIRouter(on_startup=[kafka_loop])


@router.post("/hlo_al/services/{service_id}",
             responses={
                 200: {
                     "description": "service component allocated"
                 },
                 400: {
                     "description": "invalid Service component object"
                 },
                 409: {
                     "description": "service component already exist"
                 }
             })
async def allocate_service_component(
        service_id: str,
        service_component: ServiceComponentAllocation = None,
        scomponent_network_conf: LAModels.WgClientConf = None):
    '''
    Allocate new service component in the domain
    :param service_id: ID of the service to which new component belongs.
    :param service_component: of type ServiceComponentAllocation,service component parameters
    :return: Response message and status code.
    '''
    if DEV:
        logger.info("service component: %s", service_component)
        logger.info("networking info: %s", scomponent_network_conf)
    # Check service component does not already exist and runs
    # FIXME: Take care, check again!!
    # upd: again back (was removed, think again Race conditions)
    service_exists = manager_utils.check_service_component_exists(
        service_id=service_id, service_component_id=service_component.id)
    if service_exists:
        raise HTTPException(status_code=409,
                            detail="Service component already exists")

    # Request for CR yaml file
    crd_genarator = crdGenarator.CRDGenerator()
    yaml_json = crd_genarator.generate_crd_object(
        obj=service_component,
        obj_net=scomponent_network_conf,
        service_id=service_id)
    yaml_obj = yaml.dump(yaml_json)
    logger.info("YAML_Object: %s", yaml_obj)
    # Send for LLO REST API
    llo_client = LLORESTClient()
    try:
        status_code, deployment_response = llo_client.request_deployment(
            yaml_str=yaml_obj)
    except TypeError as er:
        logger.error("Error happned: %s", er)
        status_code = 400
        deployment_response = "Something bad happened"
    # Some logging
    logger.info('LLO REST API Response for service: %s, the component:',
                service_id)
    logger.info("Status code from update is: %s", status_code)
    logger.info("Response is: %s", deployment_response)
    # Update service component status in the aeriOS contiunuum
    if status_code == 201:
        manager_utils.set_service_component_status(
            service_id=service_id,
            scomponent_id=service_component.id,
            scomponent_status=aeriOS_c.ServiceComponentStatusEnum.RUNNING)
        manager_utils.set_service_component_ie(
            service_id=service_id,
            scomponent_id=service_component.id,
            allocated_ie_id=service_component.infrastructure_element.id)
        # return {"status": "service component allocated"}
        return JSONResponse(
            status_code=201,
            content={
                "status":
                f"service component allocated for service component: : {service_id} "
            })
    else:
        manager_utils.set_service_component_status(
            service_id=service_id,
            scomponent_id=service_component.id,
            scomponent_status=aeriOS_c.ServiceComponentStatusEnum.FAILED)
        return JSONResponse(
            status_code=400,
            content={
                "status":
                f"Failed to allocate service component: {service_id} "
            })


@router.get(
    "/hlo_al/services/{service_id}/service_components/{service_component_id}",
    responses={
        200: {
            "model": ServiceComponentParameters,
            "description": "service component allocation parameters updated"
        },
        404: {
            "description": "service component parameters",
            "model": ServiceComponentNotAllocated,
        }
    })
async def get_scomponent_parameters(service_id: str,
                                    service_component_id: str):
    '''
    Get the service component allocation parameters in the domain

    :param service_id: The ID of the service (path parameter).
    :param service_component_id: The ID of the service (path parameter).
    :return: Information about the service component.
    '''
    service_exists = manager_utils.check_service_component_exists(
        service_id=service_id, service_component_id=service_component_id)
    if not service_exists:
        raise HTTPException(status_code=404,
                            detail="Service Component not Allocated")
    llo_client = LLORESTClient()
    deployment_parametrs = llo_client.get_deployment_parameters(
        scomponent_id=service_component_id)
    if not deployment_parametrs:
        raise HTTPException(status_code=404,
                            detail="Service Component not Allocated [LLO]")
    return deployment_parametrs


@router.put(
    "/hlo_al/services/{service_id}/service_components/{service_component_id}",
    responses={
        200: {
            "description": "service component allocation parameters updated"
        },
        400: {
            "description": "invalid Service component parameters object"
        },
        404: {
            "description": "service component already exist",
            "model": ServiceComponentNotAllocated,
        }
    })
async def update_scomponent_parameters(service_id: str,
                                       service_component_id: str,
                                       parameters: ServiceComponentParameters):
    '''
    Update allocation parameters of an existing service component in the domain
    '''
    service_exists = manager_utils.check_service_component_exists(
        service_id=service_id, service_component_id=service_component_id)
    if not service_exists:
        raise HTTPException(status_code=404,
                            detail="Service Component not Allocated")

    # FIXME:Ask Rafa what it means update

    return {"status": "service component update"}


@router.delete(
    "/hlo_al/services/{service_id}/service_components/{service_component_id}",
    responses={
        200: {
            "description": "Service component deallocated"
        },
        404: {
            "model": ServiceComponentAllocation,
            "description": "Service Component not allocated"
        }
    })
async def deallocate_scomponents(service_id: str, service_component_id: str):
    '''
    Deallocate an existing service component in the domain
    '''
    # upd: again back (was removed, think again Race conditions)
    service_exists = manager_utils.check_service_component_exists(
        service_id=service_id, service_component_id=service_component_id)
    if not service_exists:
        raise HTTPException(status_code=404,
                            detail="Service Component not allocated")
    hosting_ie = manager_utils.get_scompnent_hosting_ie(
        scomponent_id=service_component_id)
    llo_type = manager_utils.get_ie_llo_type(hosting_ie)

    llo_client = LLORESTClient()
    status_code = llo_client.request_delete_deployment(
        scomponent_id=service_component_id, llo_type=llo_type)

    # logger.info('LLO REST API Response for service: %s, the component:',
    #             service_id)
    # logger.info(service_component_id)
    logger.info("Response status from delete is %s", status_code)

    # TODO:
    # Check response from LLO, no response or status code is returned
    # if status_code == 200:

    # FIXME: We need to tell if it comes from deallocate, as at that case we whould not update service status
    # because it is a race condition with new HLO-LA who will update the last
    manager_utils.set_service_component_status(
        service_id=service_id,
        scomponent_id=service_component_id,
        scomponent_status=aeriOS_c.ServiceComponentStatusEnum.FINISHED)
    manager_utils.set_service_component_ie(service_id=service_id,
                                           scomponent_id=service_component_id,
                                           allocated_ie_id="urn:ngsi-ld:null")
    return {"status": "Service component deallocated"}


@router.delete("/hlo_al/services/{service_id}/overlay",
               responses={
                   200: {
                       "description": "Service overlay delete"
                   },
                   404: {
                       "description": "Service ovelray not destroyed"
                   }
               })
async def destroy_service_overlay(service_id: str):
    '''
    Destroy an existing service overlay domain
    This domain had recieved intial allocation request and thus provides overlay
    '''
    logger.info("Deleting overlay subnet allocated for %s", service_id)
    service_exists = manager_utils.check_service_exists(service_id=service_id)
    if not service_exists:
        raise HTTPException(status_code=404, detail="Service not found")
    k8s_shim_client.delete_wireguard_overlay_allocation(service_id=service_id)
