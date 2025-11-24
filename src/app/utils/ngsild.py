'''
    Module with all functions to create pydantic objects for aeriOS continuum entities
'''
# from typing import List
from app.api_clients.cb_client import CBClient
import app.app_models.aeriOS_continuum as aeriOS_C


def get_aeriOS_orginization(entity_id) -> aeriOS_C.Organization:
    """Get Organization from aeriOS"""
    cb_client = CBClient()
    aeriOS_org_json = cb_client.query_entity(entity_id=entity_id,
                                            ngsild_params='format=simplified')
    org_py = aeriOS_C.Organization(**aeriOS_org_json)
    return org_py


def get_aeriOS_domain(entity_id) -> aeriOS_C.Domain:
    """Get Domain from aeriOS"""
    cb_client = CBClient()
    aeriOS_domain_json = cb_client.query_entity(
        entity_id=entity_id, ngsild_params='format=simplified')
    domain_py = aeriOS_C.Domain(**aeriOS_domain_json)
    org_py = get_aeriOS_orginization(
        domain_py.owner[0])  # FIXME, will there be many Owners ?
    domain_py.owner = org_py
    return domain_py


def get_aeriOS_llo(entity_id) -> aeriOS_C.LowLevelOrchestrator:
    """Get LowLevelOrchestrator from aeriOS"""
    cb_client = CBClient()
    aeriOS_llo_json = cb_client.query_entity(entity_id=entity_id,
                                            ngsild_params='format=simplified')
    aeriOS_llo_py = aeriOS_C.LowLevelOrchestrator(**aeriOS_llo_json)
    domain_py = get_aeriOS_domain(aeriOS_llo_py.domain)
    aeriOS_llo_py.domain = domain_py
    return aeriOS_llo_py
