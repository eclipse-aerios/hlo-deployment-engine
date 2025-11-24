'''
    Client to access Local Allocation Manager of selected domain.
    Module which handles requests to selected aeriOS domain for workload palcement.
    Requests verify is set to False  
      to avoid failing with self signed-certificates used for aeriOS domains in private LANs
    TBD: integrate remote pem files instead of using verify false
'''
import concurrent.futures
import requests
from app.utils.decorators import catch_requests_exceptions
from app.app_models.py_files import hlo_pb2 as hlo
from app.localAllocationManager.models import ServiceComponentAllocation, InfrastructureElementCR
from app.utils.log import get_app_logger
import app.utils.continuum_utils as c_utils
from app.api_clients import k8s_shim_client
from app.localAllocationManager.models import WgClientConf  #, ServiceComponentAllocation
from app.config import DEV
import app.app_models.aeriOS_continuum as aeriOS_c


class HLOALClient:
    '''
        Client for Local Allocation Manager
    '''

    def __init__(self, api_url):
        self.logger = get_app_logger()
        self.logger.info("Setting remote HLO_AL URL")
        self.api_url = api_url  # API URL of selected domain
        self.m2m_hlo_token = k8s_shim_client.get_m2m_hlo_token()
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.m2m_hlo_token}'
        }
        self.logger.info(
            "Called with api_url argument: %s and now our domain api_url for hlo_al is: %s ",
            api_url, self.api_url)
        self.logger.info("HLO_AL headers: %s", self.headers)

    @catch_requests_exceptions
    def request_deallocate_scompenent(
        self,
        service_component_id: str,
        service_id: str,
    ):
        '''
            Deallocate service request to Local Allocation Manager
        '''
        if not service_id:
            # based on the naming convention: [urn:ngsi-ld]:[Service:05]:[Component:02]
            scomponent_id = service_component_id
            parts = scomponent_id.split(':')
            service_id = ':'.join(parts[:4])  ### REMOVE HERE TOO
        delete_url = f'{self.api_url}/hlo_al/services/{service_id}/service_components/{service_component_id}'
        response = requests.delete(url=delete_url,
                                   headers=self.headers,
                                   timeout=15,
                                   verify=False)
        response.raise_for_status()
        return response.status_code

    @catch_requests_exceptions
    def request_allocate_scompenent(
            self,
            scomponent_allocation: hlo.ServiceComponent,
            overlay_conf: WgClientConf = None,
            service_id: str = ""):
        '''
            Allocate service request to Local Allocation Manager
            Create ServiceComponentAllocation Objcet as expected from Local Allocation manager
            :param: service_id: the service for which to request service component deployment
            :param: deploymentEngine.ServiceComponent 
                      as part of deploymentEngine.ServiceComponentAlloaction
                        which is list element of HLODeploymentEngineInput
                            of protobuf input list
        '''
        self.logger.info("Overlay conf: %s and  component conf: %s",
                         overlay_conf, scomponent_allocation)
        if not service_id:
            # based on the naming convention: [urn:ngsi-ld]:[Service:05]:[Component:02]
            scomponent_id = scomponent_allocation.id
            parts = scomponent_id.split(':')
            service_id = ':'.join(parts[:4])

        expected_orchestration_type = scomponent_allocation.infrastructure_element.container_technology
        if expected_orchestration_type == "Kubernetes":
            orchestrator_config = "ServiceComponentK8s"
        elif expected_orchestration_type == "Docker":
            orchestrator_config = "ServiceComponentDocker"
        else:
            # Should never come here!
            orchestrator_config = ""
        ports_list = []

        for port in scomponent_allocation.ports:
            port_obj = {"number": port.number}
            ports_list.append(port_obj)

        cliargs_list = []
        for arg in scomponent_allocation.cliArgs:
            arg_obj = {"key": arg.key, "value": arg.value}
            cliargs_list.append(arg_obj)
        envvars_list = []
        for arg in scomponent_allocation.envVars:
            arg_obj = {"key": arg.key, "value": arg.value}
            envvars_list.append(arg_obj)

        infrastructure_element_json = {
            "hostname": scomponent_allocation.infrastructure_element.hostname,
            "id": scomponent_allocation.infrastructure_element.id
        }
        ie_cr = InfrastructureElementCR(**infrastructure_element_json)
        allocation_obj_json = ServiceComponentAllocation(
            id=scomponent_allocation.id,
            orchestration_type=orchestrator_config,
            image=scomponent_allocation.image,
            infrastructure_element=ie_cr,
            ports=ports_list,
            cliArgs=cliargs_list,
            envVars=envvars_list,
            llo_id=scomponent_allocation.infrastructure_element.
            low_level_orchestrator.id,
            exposePorts=scomponent_allocation.exposePorts,
            isJob=scomponent_allocation.isJob,
            isPrivate=scomponent_allocation.is_private,
            repoUsername=scomponent_allocation.credentials.username,
            repoPassword=scomponent_allocation.credentials.password)

        allocate_url = f'{self.api_url}/hlo_al/services/{service_id}'

        if DEV:
            self.logger.info("SCOMPONENT: %s",
                             allocation_obj_json.model_dump_json())
            if overlay_conf:
                self.logger.info("NETWORK: %s", overlay_conf.model_dump_json())
            else:
                self.logger.info("NETWORK: Not requested for this service")

        payload = {
            "service_component": allocation_obj_json.model_dump()
        }
        # If we have overlay, we need to add it to the payload
        # If overlay_conf is empty dict {}, we do not add it to the payload
        if overlay_conf:
            payload["scomponent_network_conf"] = overlay_conf.model_dump()

        response = requests.post(url=allocate_url,
                                 json=payload,
                                 headers=self.headers,
                                 timeout=15,
                                 verify=False)
        # From this point on we move to Local Allocation Manager component, i.e. REST API exposed
        # response.raise_for_status()
        self.logger.info('HLOALClient response for create: %s',
                         response.json())
        if DEV:
            self.logger.info('Headers: %s', response.headers)
        return response

    @catch_requests_exceptions
    def request_destroy_service_overlay(self, service_id: str):
        '''
            Request to destroy service overlay to Local Allocation Manager
              :param: service_id: the service for which to request overlay destroy
        '''
        if DEV:
            self.logger.info("URL: %s", self.api_url)
        destroy_overlay_url = f'{self.api_url}/hlo_al/services/{service_id}/overlay'
        response = requests.delete(url=destroy_overlay_url,
                                   headers=self.headers,
                                   timeout=15,
                                   verify=False)
        # response.raise_for_status()
        return response.status_code


####################################################################################################
###### End of class, Start parallel objects method calls ###########################################
####################################################################################################


# Function to call API request of HLOALClient instances (remote -maybe local- domains)
def call_method(instance, method_name, params):
    '''
    Calls method of an object:
    Inputs:
        instance: th instance of the class
        method_name: the method of the object to call
        params: dictionairy with 'key':'value' of method parameters

    '''
    method = getattr(instance, method_name)
    return method(**params)  # Call the method with any parameters


def submit_remote_allocations(hloalclients_list: list):
    '''
    Method to dispatch parallel threads for calling remote domains local allocation managers
    Inputs:
        list of [hloclient_object, method, params_dict]
    '''
    logger = get_app_logger()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit each method call to be run in a separate thread
        future_to_method = {
            executor.submit(call_method, instance, method_name, params):
            (instance, method_name, params)
            for instance, method_name, params in hloalclients_list
        }

        # Collect and print the results as they complete
        for future in concurrent.futures.as_completed(future_to_method):
            instance, method_name, params = future_to_method[future]
            try:
                result = future.result()
                logger.info(
                    "Method: %s called with params %s and result is %s",
                    method_name, params, result)
                # if result != 201:
                #     c_utils.set_service_component_status(
                #         service_id=params['service_id'],
                #         scomponent_id=params['scomponent_allocation'].id,
                #         scomponent_status=aeriOS_c.ServiceComponentStatusEnum.
                #         FAILED)
            except Exception as exc:
                logger.error(
                    "Method %s with params %s generated an exception: %s",
                    method_name, params, exc)
                c_utils.set_service_component_status(
                    service_id=params['service_id'],
                    scomponent_id=params['scomponent_allocation'].id,
                    scomponent_status=aeriOS_c.ServiceComponentStatusEnum.FAILED
                )

# To test delays between allocation requests
# import time
# def submit_remote_allocations(hloalclients_list: list):
#     '''
#     Method to dispatch parallel threads for calling remote domains' local allocation managers
#     Inputs:
#         list of [hloclient_object, method, params_dict]
#     '''
#     logger = get_app_logger()

#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         future_to_method = {}

#         # Submit each method call with a 1-second delay
#         for instance, method_name, params in hloalclients_list:
#             future = executor.submit(call_method, instance, method_name,
#                                      params)
#             future_to_method[future] = (instance, method_name, params)
#             time.sleep(
#                 1
#             )  # Introduce a 1-second delay before submitting the next task

#         # Collect and print the results as they complete
#         for future in concurrent.futures.as_completed(future_to_method):
#             instance, method_name, params = future_to_method[future]
#             try:
#                 result = future.result()
#                 logger.info(
#                     "Method: %s called with params %s and result is %s",
#                     method_name, params, result)
#             except Exception as exc:
#                 logger.error(
#                     "Method %s with params %s generated an exception: %s",
#                     method_name, params, exc)
#                 c_utils.set_service_component_status(
#                     service_id=params['service_id'],
#                     scomponent_id=params['scomponent_allocation'].id,
#                     scomponent_status=aeriOS_c.ServiceComponentStatusEnum.FAILED
                # )
