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
module: cloudflare_account_lb_info
short_description: Gather information about Cloudflare load balancer pools
description:
  - Gather information about a Cloudflare load balancer pool
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
'''

EXAMPLES = '''
- cloudflare_account_lb_info: >
    account_id=321423423gfd239sfda9afd0123e20
    email=joe@example.com
    api_key=77a54a4c36858cfc10321fcfce22378e19e20
'''


RETURN = '''
clbs:
    description: A list of dicts describing the account lb
    returned: always
    type: list
    sample:
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
    def __init__(self, email, api_key, account_id):
        self.url = "https://api.cloudflare.com/client/v4/accounts/" + \
                     "{account_id}/load_balancers/pools".format(account_id=account_id)
        self.email = email
        self.api_key = api_key

    def request(self, method, **kwargs):
        # remove unset
        kwargs = dict((k, v) for k, v in kwargs.iteritems() if v)

        # Instantiate custom request
        handler = urllib2.HTTPHandler()
        opener = urllib2.build_opener(handler)
        request = urllib2.Request(self.url)

        # Add headers
        request.add_header("Content-Type", 'application/json')
        request.add_header('X-Auth-Email', self.email)
        request.add_header('X-Auth-Key', self.api_key)

        request.get_method = lambda: method
        connection = opener.open(request)
        response_json = json.loads(connection.read())

        return response_json

    def rec_info(self):
        return self.request(a='rec_info', method='GET')


def cloudflare_account_lb(module):
    cloudflare = Cloudflare(module.params['email'],
                            module.params['api_key'],
                            module.params['account_id'])
    return cloudflare.rec_info()

def main():
    module = AnsibleModule(
        argument_spec=dict(
            account_id=dict(required=True),
            email=dict(no_log=False, default=os.environ.get('CLOUDFLARE_API_EMAIL')),
            api_key=dict(no_log=False, default=os.environ.get('CLOUDFLARE_API_TOKEN')),
        ),
        supports_check_mode=False,
    )

    try:
        request = cloudflare_account_lb(module)
    except Exception as err:
        module.fail_json(msg=str(err))

    module.exit_json(clbs=request.get('result'))

if __name__ == '__main__':
    main()
