'''
    Docstring
'''
from typing import List, Optional
from pydantic import BaseModel


class Port(BaseModel):
    '''
    Exposing Port(s) for service component
    '''
    number: int


class CliArgs(BaseModel):
    '''
        Added to model cliArgs according to CRD
    '''
    key: str
    value: Optional[str] = None


class EnvVars(BaseModel):
    '''
        Added to model cliArgs according to CRD
    '''
    key: str
    value: Optional[str] = None


class InfrastructureElementCR(BaseModel):
    '''
    Type IE format as needed for CR for LLO
    '''
    hostname: str
    id: str


class ServiceComponentParameters(BaseModel):
    '''
    Object for updating existing service component
    FIXME: Missing in REST API Body
            a) orchestration_type: "urn:ngsi-ld:OrchestrationType:Kubernetes/Docker" 
                mapped to "kind: ServiceComponentDocker/K8s" 
            b) service component name for "app.kubernetes.io/name: component-1-of-the-service-1"
            d) LLO name for "app.kubernetes.io/created-by: urn_ngsi-ld_LowLevelOrchestrator_1"
           Service id is OK for "app.kubernetes.io/part-of: urn_ngsi-ld_Service_1", we have from path parameter
    '''
    image: str
    envVars: Optional[List[EnvVars]] = []
    cliArgs: Optional[List[CliArgs]] = []
    infrastructure_element: InfrastructureElementCR
    ports: List[Port] = []
    orchestration_type: str
    llo_id: Optional[str]
    exposePorts: bool
    isJob: Optional[bool] = None
    isPrivate: Optional[bool] = None
    repoUsername: Optional[str] = None
    repoPassword: Optional[str] = None


class ServiceComponentAllocation(ServiceComponentParameters):
    '''
    Object for allocating a new service component
    '''
    id: str


class ServiceComponentNotAllocated(BaseModel):
    '''
    Allocation failure response object 
    '''
    description: str


class WgClientConf(BaseModel):
    """
    Class to type configuration expected for wg clients
    """
    Address: str
    DNS: str
    PublicKey: str
    Endpoint: str
    AllowedIPs: str
    PrivateKey: str


class AllocationPayload(BaseModel):
    """
    Class to model total allocation
    """
    service_component: ServiceComponentAllocation
    scomponent_network_conf: WgClientConf
