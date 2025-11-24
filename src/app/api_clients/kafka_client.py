'''
    Protobuf and kafka related functions
'''
from app.utils.log import get_app_logger
from app.app_models.py_files  import deployment_engine_pb2 as deployment_engine


logger = get_app_logger()

###################################################
############ BINARY PROTOBUF  #####################

def parse_from_bytes(data):
    '''
        Parse received kafka protobuf message from binary to string
    '''
    data_input = deployment_engine.HLODeploymentEngineInput()
    data_input.ParseFromString(data)
    return data_input





