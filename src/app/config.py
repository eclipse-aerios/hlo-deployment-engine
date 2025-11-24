'''
    Docstring
'''
import os
# from app.localAllocationManager.models import ServiceComponentParameters, Port

# Set DEV to False when building production container images
DEV = False
if DEV:
    # CB_URL = 'https://ncsrd-mvp-domain.aeriOS-project.eu'
    # CB_PORT = '443'
    # URL_VERSION = ''
    # Orion-LD configuration
    CB_URL = 'http://10.220.2.101'  # <=== node IP for node port
    CB_PORT = '31026'  # <== exposed node port
    URL_VERSION = 'ngsi-ld/v1/'
    DEV_HLO_AL_URL = 'http://localhost'
    # HLO_AL_URL = 'ncsrd-mvp-domain.aeriOS-project.eu'
    DEV_HLO_AL_PORT = '8082'
    # HLO_AL_PORT = '443'
    LLO_REST_URL = 'http://10.220.2.101'
    LLO_REST_PORT = '30890'
    CONSUMER_TOPIC = 'allocator2deployment_dev'
    K8S_SHIM_URL = 'http://localhost'
    K8S_SHIM_PORT = '5000'
else:
    CB_URL = os.environ.get('CB_URL')
    CB_PORT = os.environ.get('CB_PORT')
    URL_VERSION = 'ngsi-ld/v1/'
    LLO_REST_URL = os.environ.get('LLO_REST_URL')
    LLO_REST_PORT = os.environ.get('LLO_REST_PORT')
    CONSUMER_TOPIC = os.environ.get('CONSUMER_TOPIC')
    K8S_SHIM_URL = os.environ.get('K8S_SHIM_URL')
    K8S_SHIM_PORT = os.environ.get('K8S_SHIM_PORT')

TOKEN_URL = f"{K8S_SHIM_URL}:{K8S_SHIM_PORT}/token"
WG_SERVER_URL = f"{K8S_SHIM_URL}:{K8S_SHIM_PORT}"

PARENT_PATH = os.path.dirname(__file__)
LOG_PATH = PARENT_PATH + '/log/local_allocation_manager.log'

# RedPanda prosumer configurations
consumer_config = {
    'bootstrap.servers':
    os.environ.get('BOOTSTRAP_SERVERS',
                   'redpanda-0.redpanda.redpanda.svc.cluster.local:9093'),
    'group.id':
    os.environ.get('GROUP_ID', 'python-consumer'),
    'auto.offset.reset':
    os.environ.get('AUTO_OFFSET_RESET', 'earliest')
}
