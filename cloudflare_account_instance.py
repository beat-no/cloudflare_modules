#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This is a free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This Ansible library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.
#
# Please refer to both the ansible and cloudflare official documentation
# for development on this module:
# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_general.html
# https://api.cloudflare.com/#account-load-balancer-pools-properties


import json
import urllib2
import os

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = '''
---
module: cloudflare_account_instance
short_description: De-registers or registers instances from cloudflare CLBs
description:
  - This module de-registers or registers an instance from pre defined pools
  - Will be marked changed when called only if a existing pool and account is matched
author: Beat beat.no
options:
  account_id:
    description: Identifier of the load balancer account
    required: true
  api_key:
    description:
      - This is the API key made available on your CloudFlare account page.
      - This can also be provided by setting the CLOUDFLARE_API_TOKEN environment variable.
    required: true
  email:
    description:
      - The e-mail address associated with the API key.
      - This can also be provided by setting the CLOUDFLARE_API_EMAIL environment variable.
    required: true
  pool_id:
    description: Identifier of the load balancer pool
    required: true
  state:
    description: Register or deregister the instance
    choices: ['present', 'absent']
    required: true
  instance_ip
    description: IP of instance
    required: true
  instance_name:
    description: Name of instance
    required: true
  instances_weight:
    description: Weight attributed to an instance
    required: false
  wait:
    description: Wait for instance registration or deregistration to complete successfully before returning.
    choices: ['true', 'false']
    required: false
'''

EXAMPLES = '''
- cloudflare_account_instance: >
    account_id=321423423gfd239sfda9afd0123e20
    email=joe@example.com
    api_key=77a54a4c36858cfc10321fcfce22378e19e20
    state=present
    instance_ip="0.0.0.0"
    instance_name=example_server42
    instance_weight=1.0
'''


RETURN = '''
clbs:
    [{
      "check_regions": [
        "ABCD"
      ],
      "description": "",
      "origins": [
        {
          "enabled": true,
          "name": "example_server3",
          "weight": 1,
          "address": "0.0.0.0"
        },
        {
          "enabled": true,
          "name": "example_server2",
          "weight": 1,
          "address": "0.0.0.0"
        },
        {
          "enabled": true,
          "name": "example_server1",
          "weight": 1,
          "address": "0.0.0.0"
        },
        {
          "enabled": true,
          "name": "example_server0",
          "weight": 1,
          "address": "0.0.0.0"
        }
      ],
      "enabled": true,
      "created_on": "1814-05-17T09:46:07.281116Z",
      "minimum_origins": 1,
      "modified_on": "1814-05-17T09:46:07.281116Z",
      "notification_email": "email@notification.com",
      "id": "fdsao99fdas9fdsaklkfdsa9fdas",
      "name": "lb_name"
    }]
'''

class CloudflareException(Exception):
    pass

class Cloudflare(object):
    def __init__(self, email, api_key, account_id, pool_id,
                 state, instance_ip, instance_name, instance_weight, wait):
        self.base_url = "https://api.cloudflare.com/client/v4/accounts/" + \
            "{account_id}/load_balancers/pools".format(account_id=account_id)
        self.url = self.base_url + "/{pool_id}".format(pool_id=pool_id)
        self.pool_id = pool_id
        self.email = email
        self.api_key = api_key
        self.state = state
        self.instance_ip = instance_ip
        self.instance_name = instance_name
        self.instance_weight = instance_weight
        self.wait = wait


    def request(self, content, **kwargs):
        # remove unset
        kwargs = dict((k, v) for k, v in kwargs.iteritems() if v)

        # Instantiate custom request
        handler = urllib2.HTTPHandler()
        opener = urllib2.build_opener(handler)

        # Is it a get or put request
        if content is None:
            request = urllib2.Request(self.base_url)
            request.get_method = lambda: 'GET'
        else:
            request = urllib2.Request(self.url)
            request.get_method = lambda: 'PUT'
            request.data = content

        # Add headers
        request.add_header("Content-Type", 'application/json')
        request.add_header('X-Auth-Email', self.email)
        request.add_header('X-Auth-Key', self.api_key)

        connection = opener.open(request)
        response_json = json.loads(connection.read())
        return response_json


    def req_present(self):
        current_state = self._req_pool_info()
        current_pool_name = current_state.get('name')
        origins = current_state.get('origins')

        # new origin does not exist in current origin?
        if self._get_origin_by_ip(origins) is not None:
            raise CloudflareException('Origin requested to be present already exists')

        # new origin to be added
        new_origin = {
		    "enabled": True,
		    "name": self.instance_name,
            "weight": self.instance_weight,
            "address": self.instance_ip,
	    }

        origins.append(new_origin)

        # create minimal object that cloudflare api will accept
        desired_state = json.dumps({
            "name": current_pool_name,
            "origins": origins,
        })
        return self.request(a='req_present', content=desired_state)


    def req_absent(self):
        current_state = self._req_pool_info()
        current_pool_name = current_state.get('name')
        origins = current_state.get('origins')
        desired_origins_state = list(filter(lambda i: i['address'] != self.instance_ip, origins))

        # new origins contains at least one origin
        if len(desired_origins_state) <= 1:
            raise CloudflareException('Cloudflare requires origin to contain at least one entry')

        desired_state = json.dumps({
            "name": current_pool_name,
            "origins": desired_origins_state
        })
        return self.request(a='req_absent', content=desired_state)

    def _req_pool_info(self):
        """
        Return JSON containing all information about lb pool:
        {
          'check_regions':[
                'WNAM'
          ],
          'description':'',
          'origins':[
             {
                      'enabled': True,
                      'name': 'example_server0',
                      'weight': 1,
                      'address': '0.0.0.0'
             }
          ],
          'enabled':False,
          'created_on':'1814-05-17T09:46:07.281116Z',
          'minimum_origins':1,
          'modified_on':'1914-05-17T12:34:31.398522Z',
          'notification_email':'',
          'id':'320fd09sa09fdsa98a09sfd098saf',
          'name':'pool_name'
        }
        """
        pools = self.request(a='_req_pool_info', content=None).get('result')
        selected_pool = next((item for item in pools if item['id'] == self.pool_id), None)
        return selected_pool


    def _get_origin_by_ip(self, origins):
        return next((item for item in origins if item['address'] == self.instance_ip), None)


def cloudflare_account_instance(module):
    cloudflare = Cloudflare(module.params['email'],
                            module.params['api_key'],
                            module.params['account_id'],
                            module.params['pool_id'],
                            module.params['state'], # NOTE
                            module.params['instance_ip'],
                            module.params['instance_name'],
                            module.params['instance_weight'],
                            module.params['wait'],)

    state = module.params['state']

    if state == 'present':
        resp = cloudflare.req_present()
        module.exit_json(changed=True, response=resp)

    elif state == 'absent':
        resp = cloudflare.req_absent()
        module.exit_json(changed=True, response=resp)

    module.fail_json(msg='Unknown value "{0}" for argument state. Expected one of: present, absent.')

def main():
    module = AnsibleModule(
        argument_spec=dict(
            account_id=dict(required=True),
            pool_id=dict(required=True),
            email=dict(no_log=False, default=os.environ.get('CLOUDFLARE_API_EMAIL')),
            api_key=dict(no_log=False, default=os.environ.get('CLOUDFLARE_API_TOKEN')),
            state=dict(required=True, choices=['present', 'absent']),
            instance_ip=dict(required=True),
            instance_name=dict(required=True),
            instance_weight=dict(required=False, default=1.0, type=float),
            wait=dict(required=False, default=False, type=bool),
        ),
        supports_check_mode=False,
    )

    try:
        req = cloudflare_account_instance(module)
    except Exception as err:
        module.fail_json(msg=str(err))

    module.exit_json(clbs=req)

if __name__ == '__main__':
    main()
