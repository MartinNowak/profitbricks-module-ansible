#!/usr/bin/python
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

ANSIBLE_METADATA = {'status': ['preview'],
                    'supported_by': 'community',
                    'version': '1.0'}

DOCUMENTATION = '''
---
module: profitbricks_volume_attachments
short_description: Attach or detach a volume.
description:
     - Allows you to attach or detach a volume from a ProfitBricks server.
version_added: "2.0"
options:
  datacenter:
    description:
      - The datacenter in which to operate.
    required: true
  server:
    description:
      - The name of the server you wish to detach or attach the volume.
    required: true
  volume:
    description:
      - The volume name or ID.
    required: true
  subscription_user:
    description:
      - The ProfitBricks username. Overrides the PROFITBRICKS_USERNAME environement variable.
    required: false
  subscription_password:
    description:
      - THe ProfitBricks password. Overrides the PROFITBRICKS_PASSWORD environement variable.
    required: false
  wait:
    description:
      - wait for the operation to complete before returning
    required: false
    default: "yes"
    choices: [ "yes", "no" ]
  wait_timeout:
    description:
      - how long before wait gives up, in seconds
    default: 600
  state:
    description:
      - Indicate desired state of the resource
    required: false
    default: "present"
    choices: ["present", "absent"]

requirements:
    - "python >= 2.6"
    - "profitbricks >= 4.0.0"
author:
    - "Matt Baldwin (baldwin@stackpointcloud.com)"
    - "Ethan Devenport (@edevenport)"
'''

EXAMPLES = '''

# Attach a Volume

- profitbricks_volume_attachments:
    datacenter: Tardis One
    server: node002
    volume: vol01
    wait_timeout: 500
    state: present

# Detach a Volume

- profitbricks_volume_attachments:
    datacenter: Tardis One
    server: node002
    volume: vol01
    wait_timeout: 500
    state: absent

'''

import re
import uuid
import time

HAS_PB_SDK = True

try:
    from profitbricks import __version__ as sdk_version
    from profitbricks.client import ProfitBricksService, Volume
except ImportError:
    HAS_PB_SDK = False

uuid_match = re.compile(
    '[\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12}', re.I)


def _wait_for_completion(profitbricks, promise, wait_timeout, msg):
    if not promise: return
    wait_timeout = time.time() + wait_timeout
    while wait_timeout > time.time():
        time.sleep(5)
        operation_result = profitbricks.get_request(
            request_id=promise['requestId'],
            status=True)

        if operation_result['metadata']['status'] == "DONE":
            return
        elif operation_result['metadata']['status'] == "FAILED":
            raise Exception(
                'Request failed to complete ' + msg + ' "' + str(
                    promise['requestId']) + '" to complete.')

    raise Exception(
        'Timed out waiting for async operation ' + msg + ' "' + str(
            promise['requestId']
            ) + '" to complete.')


def attach_volume(module, profitbricks):
    """
    Attaches a volume.

    This will attach a volume to the server.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Returns:
        True if the volume was attached, false otherwise
    """
    datacenter = module.params.get('datacenter')
    server = module.params.get('server')
    volume = module.params.get('volume')

    # Locate UUID for Datacenter
    if not (uuid_match.match(datacenter)):
        datacenter_list = profitbricks.list_datacenters()
        for d in datacenter_list['items']:
            dc = profitbricks.get_datacenter(d['id'])
            if datacenter == dc['properties']['name']:
                datacenter = d['id']
                break

    # Locate UUID for Server
    if not (uuid_match.match(server)):
        server_list = profitbricks.list_servers(datacenter)
        for s in server_list['items']:
            if server == s['properties']['name']:
                server = s['id']
                break

    # Locate UUID for Volume
    if not (uuid_match.match(volume)):
        volume_list = profitbricks.list_volumes(datacenter)
        for v in volume_list['items']:
            if volume == v['properties']['name']:
                volume = v['id']
                break

    return profitbricks.attach_volume(datacenter, server, volume)


def detach_volume(module, profitbricks):
    """
    Detaches a volume.

    This will remove a volume from the server.

    module : AnsibleModule object
    profitbricks: authenticated profitbricks object.

    Returns:
        True if the volume was detached, false otherwise
    """
    datacenter = module.params.get('datacenter')
    server = module.params.get('server')
    volume = module.params.get('volume')

    # Locate UUID for Datacenter
    if not (uuid_match.match(datacenter)):
        datacenter_list = profitbricks.list_datacenters()
        for d in datacenter_list['items']:
            dc = profitbricks.get_datacenter(d['id'])
            if datacenter == dc['properties']['name']:
                datacenter = d['id']
                break

    # Locate UUID for Server
    if not (uuid_match.match(server)):
        server_list = profitbricks.list_servers(datacenter)
        for s in server_list['items']:
            if server == s['properties']['name']:
                server = s['id']
                break

    # Locate UUID for Volume
    if not (uuid_match.match(volume)):
        volume_list = profitbricks.list_volumes(datacenter)
        for v in volume_list['items']:
            if volume == v['properties']['name']:
                volume = v['id']
                break

    return profitbricks.detach_volume(datacenter, server, volume)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            datacenter=dict(type='str'),
            server=dict(type='str'),
            volume=dict(type='str'),
            subscription_user=dict(type='str', default=os.environ.get('PROFITBRICKS_USERNAME')),
            subscription_password=dict(type='str', default=os.environ.get('PROFITBRICKS_PASSWORD')),
            wait=dict(type='bool', default=True),
            wait_timeout=dict(type='int', default=600),
            state=dict(type='str', default='present'),
        )
    )

    if not HAS_PB_SDK:
        module.fail_json(msg='profitbricks required for this module')

    if not module.params.get('subscription_user'):
        module.fail_json(msg='subscription_user parameter or ' +
            'PROFITBRICKS_USERNAME environment variable is required.')
    if not module.params.get('subscription_password'):
        module.fail_json(msg='subscription_password parameter or ' +
            'PROFITBRICKS_PASSWORD environment variable is required.')
    if not module.params.get('datacenter'):
        module.fail_json(msg='datacenter parameter is required')
    if not module.params.get('server'):
        module.fail_json(msg='server parameter is required')
    if not module.params.get('volume'):
        module.fail_json(msg='volume parameter is required')

    subscription_user = module.params.get('subscription_user')
    subscription_password = module.params.get('subscription_password')

    profitbricks = ProfitBricksService(
        username=subscription_user,
        password=subscription_password)

    user_agent = 'profitbricks-sdk-ruby/%s Ansible/%s' % (sdk_version, __version__)
    profitbricks.headers = {'User-Agent': user_agent}

    state = module.params.get('state')

    if state == 'absent':
        try:
            (changed) = detach_volume(module, profitbricks)
            module.exit_json(changed=changed)
        except Exception as e:
            module.fail_json(msg='failed to set volume_attach state: %s' % str(e))
    elif state == 'present':
        try:
            attach_volume(module, profitbricks)
            module.exit_json()
        except Exception as e:
            module.fail_json(msg='failed to set volume_attach state: %s' % str(e))

from ansible import __version__
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
