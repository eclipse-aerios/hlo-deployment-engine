"""
 Module to create CR for LLO API and thus for LLO
 Example:
    apiVersion: llo.aeriOS-project.eu/v1alpha1
    kind: ServiceComponentK8s
    metadata:
    labels:
        app.kubernetes.io/created-by: urn_ngsi-ld_LowLevelOrchestrator_NCSRD_01
        app.kubernetes.io/instance: urn_ngsi-ld_Service_05_Component_01
        app.kubernetes.io/managed-by: aeriOS-project.eu
        app.kubernetes.io/name: urn_ngsi-ld_Service_05_Component_01
        app.kubernetes.io/part-of: urn_ngsi-ld_Service_05
    name: urn-ngsi-ld-service-05-component-01
    spec:
    cliArgs:
    - key: -g
        value: daemon off;
    - key: -t
    envVars:
    - key: BACKEND_PORT
        value: '80'
    - key: BACKEND_HOST
        value: LOCALHOST
    image: nginx:latest
    ports:
    - number: 80
        protocol: TCP
    - number: 443
        protocol: TCP
    selectedIE: urn:ngsi-ld:IE:ncsrd-w1
"""
from app.localAllocationManager.models import ServiceComponentAllocation, WgClientConf
from app.utils.tools import short_label, k8s_name
    # service_slug, instance_slug, _slug, _short_label


class CRDGenerator:
    """
    Class to generate CRD for LLO API
    """

    def __init__(self):
        self.data = {
            "apiVersion": "llo.aeriOS-project.eu/v1alpha1",
            "kind": "ServiceComponentK8s",
            "metadata": {
                "labels": {
                    "app.kubernetes.io/managed-by": "aeriOS-project.eu",
                },
            },
            "spec": {}
        }

    def generate_crd_object(self,
                            obj: ServiceComponentAllocation,
                            service_id: str,
                            obj_net: WgClientConf = None):
        """
        Return CRD for LLO API
        """
        # Considered for next version
        # svc_slug = service_slug(service_id)  # -> "aeriOS-sdk-app-d363"
        # inst_slug = instance_slug(
        #     obj.id)  # -> "aeriOS-sdk-app-d363-nginx-component

        self.data["kind"] = obj.orchestration_type

        self.data["metadata"]["labels"][
            "app.kubernetes.io/name"] = short_label(obj.id)
        self.data["metadata"]["labels"][
            "app.kubernetes.io/instance"] = short_label(obj.id)
        self.data["metadata"]["labels"][
            "app.kubernetes.io/part-of"] = short_label(service_id)
        self.data["metadata"]["labels"][
            "app.kubernetes.io/created-by"] = short_label(obj.llo_id)

        # store the full URNs in annotations (no 63-char limit)
        # Considered for future implementations
        # self.data["metadata"].setdefault("annotations", {})
        # self.data["metadata"]["annotations"]["aeriOS.io/instance-urn"] = obj.id
        # self.data["metadata"]["annotations"][
        #     "aeriOS.io/service-urn"] = service_id

        # A lowercase RFC 1123 subdomain must consist of lower case alphanumeric characters, '-' or '.',
        # and must start and end with an alphanumeric character
        self.data["metadata"][
            "name"] = f'aeriOS-{k8s_name(obj.id.replace("urn:ngsi-ld:", ""))}' #f'aeriOS-{obj.id.replace("urn:ngsi-ld:", "").replace(":", "-").replace("_", "-").lower()}'
        # Specs
        self.data["spec"]["selectedIE"] = {}
        self.data["spec"]["selectedIE"][
            "id"] = obj.infrastructure_element.id  #replace("InfrastructureElement", "IE")
        self.data["spec"]["selectedIE"][
            "hostname"] = obj.infrastructure_element.hostname
        self.data["spec"]["image"] = obj.image
        if obj.isPrivate:
            self.data["spec"]["imageRegistry"] = {
                "username": obj.repoUsername,
                "password": obj.repoPassword
            }
        self.data["spec"]["exposePorts"] = obj.exposePorts
        self.data["spec"]["isJob"] = obj.isJob
        self.data["spec"]["ports"] = []
        for port in obj.ports:
            port = {"number": port.number, "protocol": "TCP"}
            self.data["spec"]["ports"].append(port)
        self.data["spec"]["cliArgs"] = []
        for item in obj.cliArgs:
            if item.value:
                arg = {"key": item.key, "value": item.value}
            else:
                arg = {
                    "key": item.key,
                }
            # FIXME: Add them when they are real
            self.data["spec"]["cliArgs"].append(arg)
        self.data["spec"]["envVars"] = []
        for item in obj.envVars:
            if item.value:
                arg = {"key": item.key, "value": item.value}
            else:
                arg = {
                    "key": item.key,
                }
            self.data["spec"]["envVars"].append(arg)

        # FIXME: Should come as a TOSCA => NGSI-LD value
        if "pi" in self.data["spec"]["selectedIE"]["hostname"]:
            self.data["spec"]["privileged"] = True

        # Overlay (wg client) configuration
        network_conf = {}
        if obj_net is not None:
            network_conf["internalIp"] = obj_net.Address
            network_conf["dns"] = obj_net.DNS
            network_conf["privateKey"] = obj_net.PrivateKey
            network_conf["publicKey"] = obj_net.PublicKey
            network_conf["endpoint"] = obj_net.Endpoint
            network_conf["allowedIps"] = obj_net.AllowedIPs
            self.data["spec"]["networkOverlay"] = network_conf

        return self.data
