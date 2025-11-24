'''
    Component runtime Control
    Subscribe to kafka and wait for events from HLO_ALLOCATOR msg 
'''
import ipaddress
# import re
from confluent_kafka import Consumer, KafkaException
from app.config import consumer_config, CONSUMER_TOPIC, DEV
from app.utils.log import get_app_logger
from app.utils import continuum_utils, tools
from app.api_clients.kafka_client import parse_from_bytes
from app.api_clients.la_manager_client import HLOALClient, submit_remote_allocations
from app.localAllocationManager import models as LAModels
from app.api_clients import k8s_shim_client
from app.api_clients import llo_api_client
from app.app_models import aeriOS_continuum as aeriOS_c
from app.utils.tools import generate_wireguard_server_url
if DEV:
    from app.config import DEV_HLO_AL_URL, DEV_HLO_AL_PORT

logger = get_app_logger()


def run():
    '''
        Staying on a loop and awaiting redpanda messages
        Messages should be binary formated and modeled according to protobuf models in gitlab:
          https://gitlab.aeriOS-project.eu/wp3/t3.3/specs 
    '''
    consumer = Consumer(consumer_config)
    # Subscribe to the topic
    consumer.subscribe([CONSUMER_TOPIC])

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                # No message was received before the timeout expired.
                continue
            if msg.error():
                if msg.error().code() == KafkaException:
                    # End of partition event
                    logger.error('%s %s reached end at offset %s\n',
                                 msg.topic(), msg.partition(), {msg.offset()})
                else:
                    logger.error('Error recceiving message: %s', msg.error())
                    raise KafkaException(msg.error())
            else:
                # Process the message
                event_data = msg.value()  #.decode('utf-8')
                logger.info('Message received: %s', event_data)

                if not event_data:
                    logger.warning("Received empty message on kafka topic, skipping")
                    consumer.commit(asynchronous=True)
                    continue

                #  Parse protobuf msg and get Service Id
                input_protbuf_msg = parse_from_bytes(event_data)
                # logger.info("Deserialize input from RedPanda: %s", input_protbuf_msg)
                if not input_protbuf_msg.service_component_allocations:
                    logger.warning(
                        "Received message with no service_component_allocations, skipping: %s",
                        input_protbuf_msg
                    )
                    consumer.commit(asynchronous=True)
                    continue
                method_calls = []
                # wg server overlay configuration object
                wg_server_obect = []

                ##########################
                # Overlay subnet used when creating new service and allocating its components
                # Indirectly check which service is orchestrated:
                #   Bad trick as allocation object "msg.service_component_allocations"
                #       does not have a direct reference to service
                #   but it is indircetly included in service components attributes.
                #   All service components arriving in the portobuf msg are part of the same service
                #   So just get the first components service attribute, it is the same for all
                first_allocation_component = input_protbuf_msg.service_component_allocations[
                    0]
                first_service_component = first_allocation_component.new_allocated_service_component
                if DEV:
                    logger.info(
                        "##################### service new_allocated_service_component: ########### %s",
                        first_service_component)
                orchestrated_service_id = first_service_component.service.id
                orchestration_action_type, has_overlay = continuum_utils.get_service_action_type(
                    orchestrated_service_id)

                # Just to avoid E0606 linter complaining
                # We should not need this
                host_domain_pk = None
                host_domain_url = None
                allowed_ips = None
                handler_domain_url = None
                overall_service_error = False

                # Update service status
                # Set from HLO-FrontEnd when action type starts and updated here that action concludes
                continuum_utils.service_handled(
                    entity_id=orchestrated_service_id,
                    action_type=orchestration_action_type)

                # Check if we need overlay for this service
                # If we have overlay, we need to create wireguard server and clients
                # If we do not have overlay, we can not proceed with service deployment
                if has_overlay:
                    logger.info("Service %s has overlay, action type: %s",
                                orchestrated_service_id,
                                orchestration_action_type)
                    # A. we are in service deploying action type,
                    #     so get all networking information needed to create overlay
                    #      i) wireguard and dnsmasquarade server localy
                    #     ii) wirguard client as scomponent sidecar in remote domains
                    if orchestration_action_type == aeriOS_c.ServiceActionTypeEnum.DEPLOYING:
                        overlay_subnet = k8s_shim_client.allocate_subnet(
                            service_id=orchestrated_service_id)
                        logger.error(
                            "Overlay subnet allocated for service %s: %s",
                            orchestrated_service_id, overlay_subnet)
                        if not overlay_subnet:
                            # with no overlay we can not proceed, set flag to use it later
                            overall_service_error = True
                            logger.error(
                                "Error while allocating subnet for service: %s",
                                orchestrated_service_id)
                        else:
                            allowed_ips = overlay_subnet
                            host_domain_url, host_domain_pk = continuum_utils.get_host_domain(
                            )
                            # e.g. if subnet is 10.0.0.0, (wg,dns)server will be 10.0.0.1
                            #      and clients will start on top of this (i.e. 10.0.0.2)
                            #      Remove subnet mask "/24" and then string to ip_address object
                            overlay_subnet_ip = ipaddress.ip_address(
                                overlay_subnet.split('/')[0])
                            wg_dns_server_overlay_ip = overlay_subnet_ip + 1
                            peer_overlay_ip = wg_dns_server_overlay_ip

                    # B. we are on service destroying
                    #   so take care to also remove service overlay
                    #   so find service handler domain and add method to call it
                    elif orchestration_action_type == aeriOS_c.ServiceActionTypeEnum.DESTROYING:
                        handler_domain_url = continuum_utils.get_service_handler_domain_url(
                            orchestrated_service_id)
                        if DEV:
                            logger.info("Using development HLO_AL")
                            overlay_handler_client = HLOALClient(
                                f'{DEV_HLO_AL_URL}:{DEV_HLO_AL_PORT}')
                        else:
                            overlay_handler_client = HLOALClient(
                                handler_domain_url)
                        method_calls.append(
                            (overlay_handler_client,
                             "request_destroy_service_overlay", {
                                 "service_id": orchestrated_service_id
                             }))

                    # C. If we are in OVERLOAD we do not have to do something on service level
                    #    as this is a component level activity

                # Now go component per component
                for allocation_component in input_protbuf_msg.service_component_allocations:
                    # a. Get (new_allocated)service_component id and
                    #           retrieve aeriOS continuum service component status
                    # b. STARTING/MIGRATING/REMOVING/OVERLOAD to act accordingly
                    # c. Get (new_allocated)service_component selcted_IE id and
                    #           retrieve selected domain URL.
                    #    Access Local Allocation Manager API for selected IE
                    #      "new_allocated_service_component.infrastructure_element.domain"
                    # d. Create Local Allocation Manager client with
                    #       Domain URL and AL_EP path and submit
                    scomponent_id = allocation_component.new_allocated_service_component.id
                    selected_ie_id = allocation_component.new_allocated_service_component.infrastructure_element.id
                    if DEV:
                        logger.info("COMPONENT RECEIVED %s: %s", scomponent_id,
                                    allocation_component)
                    selected_domain_url, selected_domain_pk = continuum_utils.get_domain_url(
                        selected_ie_id)
                    # When developing, specify domain for Local Allocation Manager to use in config file
                    if DEV:
                        logger.info("Using development HLO_AL")
                        local_alocation_client = HLOALClient(
                            f'{DEV_HLO_AL_URL}:{DEV_HLO_AL_PORT}')
                    else:
                        local_alocation_client = HLOALClient(
                            selected_domain_url)
                    # local_alocation_client = HLOALClient(selected_domain_url)

                    service_component_status = continuum_utils.get_service_component_status(
                        service_component_id=scomponent_id)
                    logger.info("Service component status received: %s",
                                service_component_status)

                    # A. Removing service component
                    if service_component_status == aeriOS_c.ServiceComponentStatusEnum.REMOVING:
                        logger.info("Deallocating %s: %s", scomponent_id,
                                    allocation_component)
                        method_calls.append((local_alocation_client,
                                             "request_deallocate_scompenent", {
                                                 "service_id":
                                                 "",
                                                 "service_component_id":
                                                 scomponent_id
                                             }))

                    # B. Allocating service component
                    elif service_component_status == aeriOS_c.ServiceComponentStatusEnum.STARTING:
                        if overall_service_error:
                            logger.error(
                                "Setting %s to failed", allocation_component.
                                new_allocated_service_component.id)
                            continuum_utils.set_service_component_status(
                                service_id=orchestrated_service_id,
                                scomponent_id=allocation_component.
                                new_allocated_service_component.id,
                                scomponent_status=aeriOS_c.
                                ServiceComponentStatusEnum.FAILED)
                        else:
                            logger.info(
                                "Service component To be allocated%s: %s",
                                scomponent_id, allocation_component)
                            # If we have overlay, we need to create overlay wg objects
                            if has_overlay:
                                # get a private/public key per service component
                                scomponent_private_key, scomponent_public_key = tools.generate_wireguard_keys(
                                )
                                peer_overlay_ip += 1
                                scomponent_name = scomponent_id.split(":")[-1]
                                conf = {
                                    "Address":
                                    str(peer_overlay_ip),
                                    "DNS":
                                    str(wg_dns_server_overlay_ip),
                                    "PublicKey":
                                    host_domain_pk,
                                    "Endpoint":
                                    generate_wireguard_server_url(
                                        host_domain_url=host_domain_url),
                                    "AllowedIPs":
                                    allowed_ips,
                                    "PrivateKey":
                                    scomponent_private_key
                                }
                                remote_wg_client_conf = LAModels.WgClientConf(
                                    **conf)
                                wg_server_obect.append({
                                    "name":
                                    f"{scomponent_name}",
                                    "peer_public_key":
                                    scomponent_public_key,
                                    "peer_overlay_ip":
                                    str(peer_overlay_ip)
                                })
                            else:
                                remote_wg_client_conf = {}
                            method_calls.append(
                                (local_alocation_client,
                                 "request_allocate_scompenent", {
                                     "service_id":
                                     "",
                                     "scomponent_allocation":
                                     allocation_component.
                                     new_allocated_service_component,
                                     "overlay_conf":
                                     remote_wg_client_conf
                                 }))

                    #C. Migrating service component
                    # CHECKME Please: Not validated!!
                    elif service_component_status == aeriOS_c.ServiceComponentStatusEnum.OVERLOAD:
                        logger.info(
                            "Overload, reallocating service component %s: %s",
                            scomponent_id, allocation_component)
                        # Selecting Domain to request de-allocation (due to overload)
                        overloaded_ie_id = allocation_component.old_allocated_infrastructure_element.id
                        overloaded_selected_domain_url = continuum_utils.get_domain_url(
                            overloaded_ie_id)
                        overloaded_local_alocation_client = HLOALClient(
                            overloaded_selected_domain_url)

                        # this seems ok, deallocate works the same......
                        method_calls.append((overloaded_local_alocation_client,
                                             "request_deallocate_scompenent", {
                                                 "service_id":
                                                 "",
                                                 "service_component_id":
                                                 scomponent_id
                                             }))
                        # a) first get network deployment obj from LLO API
                        remote_wg_client_conf = llo_api_client.LLORESTClient(
                        ).get_network_overlay_deployment_parameters(
                            scomponent_id=scomponent_id)
                        if DEV:
                            logger.info(
                                "Networking object for re-allocation: %s",
                                remote_wg_client_conf)
                        # b) send full allocation reques to remote (new) LA API
                        method_calls.append(
                            (local_alocation_client,
                             "request_allocate_scompenent", {
                                 "service_id": "",
                                 "scomponent_allocation": allocation_component.
                                 new_allocated_service_component,
                                 "overlay_conf": remote_wg_client_conf
                             }))
                    else:
                        logger.info(
                            "Could not classify service component status received: %s",
                            service_component_status)

                # We will only get in if hasOverlay is True which menas wg_server_object is not empty
                if wg_server_obect:
                    logger.info("Setting up local wireguard server")
                    # Add wireguard server details
                    wg_server_obect.append({
                        "name":
                        "WG server",
                        "peer_public_key":
                        "we_do_not_care_about_this",
                        "peer_overlay_ip":
                        str(wg_dns_server_overlay_ip),
                        "is_master":
                        True
                    })
                    # Call k8s-shim to create wg server
                    k8s_shim_client.setup_wireguard_server(
                        service_id=orchestrated_service_id,
                        wg_clients=wg_server_obect)

                logger.info("Ready to call all remote (de)allocations")
                submit_remote_allocations(method_calls)

                consumer.commit(asynchronous=True)
    except KeyboardInterrupt:
        pass
    except Exception:
        logger.exception(
            'An exception while processing msg in Deployment Engine')
    finally:
        # Close the consumer
        logger.info('Closing kafka consumer')
        consumer.close()
        run()
