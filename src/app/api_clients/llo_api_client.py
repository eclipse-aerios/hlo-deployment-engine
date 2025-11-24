'''
 aeriOS LLO REST API Client
'''
from typing import Tuple, Dict, Any, List
import requests
import app.config as config
from app.utils.log import get_app_logger
from app.utils.decorators import catch_requests_exceptions
from app.localAllocationManager.models import ServiceComponentParameters, Port, CliArgs, EnvVars, WgClientConf
from app.api_clients.cb_client import CBClient

test_str = """
apiVersion: llo.aeriOS-project.eu/v1alpha1
kind: ServiceComponentK8s
metadata:
  labels:
    app.kubernetes.io/name: component-1-of-the-service-1
    app.kubernetes.io/instance: urn_ngsi-ld_Service_1_Component_1
    app.kubernetes.io/part-of: urn_ngsi-ld_Service_1
    app.kubernetes.io/managed-by: aeriOS-project.eu
    app.kubernetes.io/created-by: urn_ngsi-ld_LowLevelOrchestrator_2
  name: service-1-component-1
spec:
  selectedIE: 
   hostname: yyy
   id: xxx
  image: fiware/orion-ld:1.5.1
  ports:
    - number: 1026
      protocol: TCP
  cliArgs:
    - key: -brokerId
      value: test-broker
    - key: -dbhost
      value: service-1-mongo
    - key: -t
      value: 0-255
    - key: -logLevel
      value: DEBUG
    - key: -forwarding
    - key: -experimental
    - key: -wip
      value: entityMaps
NetworkingInfo:
    Address   -> wg client overlay IP (10.10.1.3)
    DNS       -> overlay IP of the wg server (10.10.1.1)
    PublicKey -> remote host public key
    Endpoint  -> renote host wg server IP:port
    AllowedIPs -> overlay subnet /24  (allowedIPs)
    PrivateKey -> client private key
"""


class LLORESTClient:
    '''
        Cleint to LLO API
    '''

    def __init__(self):
        # FQDN for LLO in HELM
        self.api_url = config.LLO_REST_URL
        self.api_port = config.LLO_REST_PORT
        self.llo_rest_api_base_url = f'{self.api_url}:{self.api_port}/v1/service-components'
        # self.url_version = config.URL_VERSION
        self.headers = {
            'Content-Type': 'application/yaml',
            # 'Authorization':
            # 'Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJzaTcxSzNkUm11UFIxY2RhT2daNVFtbGpUVlR6U3JQM0cyYlZNdEVDeUVjIn0.eyJleHAiOjE3OTY3NDIyOTUsImlhdCI6MTcxMDQyODY5NSwianRpIjoiNWNiYWI4MjYtMDM3Ny00NWQ0LTk4YTItYTcwOTE4MDhhMTVlIiwiaXNzIjoiaHR0cDovL2lkbS1rZXljbG9hazo4MDgwL2F1dGgvcmVhbG1zL2tleWNsb2Fjay1vcGVubGRhcCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI5ZDY2YmEwZC0zNDc4LTQwMjQtODlkMS1lYmVkMjg0YWNhMzQiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJhZXJvcy10ZXN0Iiwic2Vzc2lvbl9zdGF0ZSI6ImM4MzA2NzEyLTkzN2EtNDU4YS1hZGU5LTNiYTI0ZGE2ZWQ5OSIsImFjciI6IjEiLCJyZWFsbV9hY2Nlc3MiOnsicm9sZXMiOlsiQ2xvdWRGZXJyb0RvbWFpbiIsImRlZmF1bHQtcm9sZXMta2V5Y2xvYWNrLW9wZW5sZGFwIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiIsIkRvbWFpbiBhZG1pbmlzdHJhdG9yIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJwcm9maWxlIGVtYWlsIiwic2lkIjoiYzgzMDY3MTItOTM3YS00NThhLWFkZTktM2JhMjRkYTZlZDk5IiwiZW1haWxfdmVyaWZpZWQiOmZhbHNlLCJuYW1lIjoiRG9tYWluIGFkbWluaXN0cmF0b3IgMSBBZG1pbiIsInByZWZlcnJlZF91c2VybmFtZSI6ImRvbWFpbmFkbWluaXN0cmF0b3IxIiwiZ2l2ZW5fbmFtZSI6IkRvbWFpbiBhZG1pbmlzdHJhdG9yIDEiLCJmYW1pbHlfbmFtZSI6IkFkbWluIn0.h7Sj7Xqu2aQg6me68sH9v5p5-hUU0qc3sWqc9teAHwB881q7tGcEsuunpHqeGf8bzTmgP50V7caoa6xGfohB-pXRSX3R6ESD415RThsPZYVXFPfUtwJWAEbR_htfPIo8Eq1p98rZPnIJJuwIjOPq4tU6sfwHF2-8c8HPR0vTwbMXEZsv1fLntEfR174DC_4J_ezAq9sY61UUUA7jRKUiX0ifokvxJR_RnNeTXPBfdPIky-je5e4whTNaHZiTxaMHLIo6VqLtCU9WsdJs9hBxLamV9fwksbQ-DeojbUc5192-gB-LA3h2hNV3rbgYYae3pHNkc2MZ0siSn7gJHaVeMg'
        }

    @catch_requests_exceptions
    def request_deployment(self, yaml_str: str) -> Tuple[int, Dict[str, Any]]:
        '''
            POST CR YAML file to LLO REST API
        '''
        entity_url = f'{self.llo_rest_api_base_url}'
        if config.DEV:
            logger = get_app_logger()
            logger.info("YAML forwarded to LLO API:\n")
            logger.info(yaml_str)
        response = requests.post(entity_url,
                                 data=yaml_str,
                                 headers=self.headers,
                                 timeout=15)
        return response.status_code, response.json()

    @catch_requests_exceptions
    def request_delete_deployment(self,
                                  scomponent_id: str,
                                  llo_type: str = 'k8s') -> int:
        """
        Send a DELETE request to the Low-Level Orchestrator (LLO) REST API
        to deallocate (undeploy) a specific service component.

        This method constructs the service name from the NGSI-LD Service Component ID
        using the naming convention defined in `crd.py`, and then issues a DELETE
        request to the LLO endpoint.

        Args:
            scomponent_id (str): The NGSI-LD URN of the Service Component to delete.
            llo_type (str, optional): The type of orchestrator to target (e.g., "k8s", "docker").
                Defaults to "k8s".

        Returns:
            int: The HTTP status code returned by the LLO API.

        Raises:
            requests.RequestException: If the DELETE request fails due to a network or timeout error.
        """
        # Construct the service name (as used in the CRD naming convention)
        service_name = f'aeriOS-{scomponent_id.replace("urn:ngsi-ld:", "").replace(":", "-").lower()}'

        # Compose the REST API URL for the target orchestrator
        entity_url = f'{self.llo_rest_api_base_url}/{service_name}?type={llo_type}'

        # Perform the DELETE request to deallocate the component
        response = requests.delete(entity_url,
                                   headers=self.headers,
                                   timeout=15)

        return response.status_code

    @catch_requests_exceptions
    def get_deployment_parameters(
            self, scomponent_id: str) -> ServiceComponentParameters:
        '''
          GET Deployment (service component) parametrs
          :param scomponent_id : the id of the service component quried
          :returns object with the parameters of the service component
        '''
        service_name = f'aeriOS-{scomponent_id.replace("urn:ngsi-ld:", "").replace(":", "-").lower()}'
        entity_url = f'{self.llo_rest_api_base_url}/{service_name}'
        response = requests.get(entity_url, headers=self.headers, timeout=15)
        response_json = response.json()
        if not "spec" in response_json.keys():
            return None
        infrastructure_element = response_json["spec"]["selectedIE"]
        image = response_json["spec"]["image"]
        isjob = response_json["spec"]["isJob"]
        expose_ports = response_json["spec"]["exposePorts"]
        # FIXME: Handle the case of private image
        if "imageRegistry" in response_json["spec"].keys():
            is_private = True
            repo_username = response_json["spec"]["imageRegistry"]["username"]
            repo_password = response_json["spec"]["imageRegistry"]["password"]
        else:
            is_private = False
            repo_username = None
            repo_password = None
        orchestration_type = response_json["kind"]
        ports: List[Port] = []
        if "ports" in response_json["spec"].keys():
            for port in response_json["spec"]["ports"]:
                p = Port(number=port["number"])
                ports.append(p)
        cli_args: List[CliArgs] = []
        if "cliArgs" in response_json["spec"].keys():
            for item in response_json["spec"]["cliArgs"]:
                if item["value"]:
                    arg = CliArgs(key=item["key"], value=item["value"])
                else:
                    arg = CliArgs(key=item["key"])
                cli_args.append(arg)
        env_vars: List[EnvVars] = []
        if "envVars" in response_json["spec"].keys():
            for item in response_json["spec"]["envVars"]:
                if item["value"]:
                    arg = EnvVars(key=item["key"], value=item["value"])
                else:
                    arg = EnvVars(key=item["key"])
                env_vars.append(arg)
        cb = CBClient()
        ngsild_params = "format=simplified"
        ie_json = cb.query_entity(
            infrastructure_element.replace(
                'IE', 'InfrastructureElement'),  # BUG in LLO naming
            ngsild_params=ngsild_params)
        llo_id = ie_json["lowLevelOrchestrator"]
        scomponent_parameters = ServiceComponentParameters(
            image=image,
            envVars=env_vars,
            cliArgs=cli_args,
            infrastructure_element=infrastructure_element,
            ports=ports,
            orchestration_type=orchestration_type,
            llo_id=llo_id,
            exposePorts=expose_ports,
            isJob=isjob,
            isPrivate=is_private,
            repoUsername=repo_username,
            repoPassword=repo_password)
        return scomponent_parameters

    @catch_requests_exceptions
    def get_network_overlay_deployment_parameters(
            self, scomponent_id: str) -> ServiceComponentParameters:
        '''
          GET Deployment (service component) parametrs
          :param scomponent_id : the id of the service component quried
          :returns object with the parameters of the wg sidecar of service component
        '''
        service_name = f'aeriOS-{scomponent_id.replace("urn:ngsi-ld:", "").replace(":", "-").lower()}'
        entity_url = f'{self.llo_rest_api_base_url}/{service_name}'
        response = requests.get(entity_url, headers=self.headers, timeout=15)
        response_json = response.json()
        network_conf = response_json["spec"]["networkOverlay"]

        network_conf_obj = WgClientConf(**network_conf)
        return network_conf_obj
