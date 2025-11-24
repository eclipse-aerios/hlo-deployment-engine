'''
Some tools
'''
import subprocess
import re
import hashlib


def generate_wireguard_keys():
    '''
    Generate wireguard keys.
    Requires wg cli installed in container
    Keys are base64 encoded (as required by wireguard)
    '''
    # Generate private key
    private_key = subprocess.check_output(['wg', 'genkey']).strip()

    # Generate public key using the private key
    process = subprocess.Popen(['wg', 'pubkey'],
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE)
    public_key, _ = process.communicate(input=private_key)
    public_key = public_key.strip()

    return private_key.decode('utf-8'), public_key.decode('utf-8')


def generate_wireguard_server_url(host_domain_url: str):
    '''
    Generate wireguard server url.
    Removes the protocol removes any existing url port and appends ":51820"
    :param host_domain_url: The continuum domain URL to process
    '''
    # Step 1: Remove the protocol (http:// or https://)
    host = re.sub(r"^https?://", "", host_domain_url)
    # Step 2: Remove everything after the first colon (if it exists)
    host = host.split(":")[0]
    # Step 3: Append the desired port ":51820"
    result = f'{host}:51820'
    return result


# A quick solution for shortening CRD metadata labels to be < 63 chars
def short_label(value: str) -> str:
    '''
    Shorten a CRD metadata label by removing the 'urn:ngsi-ld:' 
        prefix and replacing colons with underscores
    :param value: The label string to be shortened
    :type value: str
    :return: The processed label with prefix removed and colons replaced
    :rtype: str
    '''
    # 1. Remove the "urn:ngsi-ld:" prefix if present
    value = value.replace("urn:ngsi-ld:", "")
    # 2. Replace colons with underscores for consistency
    value = value.replace(":", "_")
    # 3. Replace underscores after "Component" with dash to shorten structure a bit
    # (optional, purely stylistic)
    return value


# These are not currently used but considered for in next versions
# They take care of shortening CRD metadata labels to be < 63 chars
def _slug(s: str) -> str:
    # allowed in label values: alnum, '-', '_', '.'
    s = re.sub(r'[^A-Za-z0-9._-]+', '-', s).strip('._-')
    # must start/end alnum
    s = re.sub(r'^[^A-Za-z0-9]+|[^A-Za-z0-9]+$', '', s)
    return s or "x"  # fallback


def _short_label(val: str, source_for_hash: str) -> str:
    if len(val) <= 63:
        return val
    h = hashlib.sha256(source_for_hash.encode()).hexdigest()[:8]
    return f"{val[:63-9]}-{h}"  # keep max 63 incl. hyphen + hash


def service_slug(service_urn: str) -> str:
    # e.g. "urn:ngsi-ld:Service:aeriOS-sdk-app-d363" -> "aeriOS-sdk-app-d363"
    m = re.search(r"Service:([^:]+)", service_urn)
    return _slug(m.group(1) if m else service_urn)


def instance_slug(component_urn: str) -> str:
    # e.g. "urn:ngsi-ld:Service:...:Component:nginx-component"
    ms = re.search(r"Service:([^:]+)", component_urn)
    mc = re.search(r"Component:([^:]+)", component_urn)
    parts = []
    if ms: parts.append(ms.group(1))
    if mc: parts.append(mc.group(1))
    candidate = _slug("-".join(parts) if parts else component_urn)
    return _short_label(candidate, component_urn)

def k8s_name(raw: str) -> str:
    '''
    Convert a raw string into a valid Kubernetes resource name
    by following the RFC 1123 subdomain rules.
    :param raw: The raw string to convert
    :type raw: str
    :return: A valid Kubernetes resource name
    :rtype: str
    '''
    # Lowercase
    name = raw.lower()

    # Replace invalid characters with "-"
    name = re.sub(r"[^a-z0-9.-]", "-", name)

    # Collapse multiple "-" into one
    name = re.sub(r"-+", "-", name)

    # Strip non-alphanumeric at the start/end
    name = re.sub(r"^[^a-z0-9]+", "", name)
    name = re.sub(r"[^a-z0-9]+$", "", name)

    # Kubernetes max length is 253 chars
    return name[:253]