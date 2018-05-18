# This file creates, updates and deletes a cluster admins account based on type of user(cluster and ldap).


DOCUMENTATION = '''

module: sf_user_account

short_description: Manage SolidFire cluster admins user account
author: mmkanavi
description:
- Create, destroy, or update cluster admins user account on SolidFire

options:

    state:
        description:
        - Whether the specified account should exist or not.
        required: true
        choices: ['present', 'absent']

    account_name:
        description:
        - The name of the account to manage.
        required: true

    account_password:
	description:
	- The password of cluster admin user account
	required: true

    user_type:
	description:
	- Specifies ldap or cluster user
	required: true
	
    role:
	description:
	- Specifies role's of the user account

    access:
        required: false
        choices: ["Read","Reporting", "Volumes", "Nodes", "Accounts", "Drives"]
        description:

'''

EXAMPLES = """
   - name: Create ldap account
     sf_user_account:
       hostname: "{{ solidfire_hostname }}"
       username: "{{ solidfire_username }}"
       password: "{{ solidfire_password }}"
       state: present
       account_name: "{{ solidfire_account_name }}"
       user_type: ldap
       role: system engineer

   - name: Create cluster account
     sf_user_account:
       hostname: "{{ solidfire_hostname }}"
       username: "{{ solidfire_username }}"
       password: "{{ solidfire_password }}"
       state: present
       account_name: "{{ solidfire_account_name }}"
       account_password: "{{ solidfire_account_password }}"
       user_type: cluster
       role: administrator


   - name: Update cluster admins user account
     sf_user_account:
       hostname: "{{ solidfire_hostname }}"
       username: "{{ solidfire_username }}"
       password: "{{ solidfire_password }}"
       state: present
       account_password: "{{ solidfire_account_password }}"
       account_id: 1
       access: "Reporting,Volumes" 

   - name: Delete cluster admins user account
     sf_user_account:
       hostname: "{{ solidfire_hostname }}"
       username: "{{ solidfire_username }}"
       password: "{{ solidfire_password }}"
       state: absent
       account_id: 1
"""

RETURN = """

msg:
    description: Success message
    returned: success
    type: string

"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.pycompat24 import get_exception
import ansible.module_utils.netapp as netapp_utils

HAS_SF_SDK = netapp_utils.has_sf_sdk()


class SolidFireUserAccount(object):

    def __init__(self):

        self._size_unit_map = netapp_utils.SF_BYTE_MAP

        self.argument_spec = netapp_utils.ontap_sf_host_argument_spec()
        self.argument_spec.update(dict(
            state=dict(required=False, choices=['present', 'absent']),
            account_name=dict(required=False, type='str'),
	    account_id=dict(required=False, type='int'),
	    role=dict(required=False, type='str'),
	    user_type=dict(required=False, type='str'),
	    account_password=dict(required=False, type='str'),
	    access=dict(required=False, type='str')
        ))
        
        self.module = AnsibleModule(
            argument_spec=self.argument_spec,
            supports_check_mode=True
        )
	p = self.module.params

        # set up state variables     
	self.state = p['state']
	self.account_name = p['account_name']
        self.account_id = p['account_id']
	self.role = p['role']
	self.user_type = p['user_type']
	self.account_password = p['account_password']

	if self.role == "administrator":
	    self.access = ['reporting','volumes','nodes','accounts','drives']
	elif self.role == "system engineer":
	    self.access = ['reporting','volumes']
	else:
	    self.access = ['nodes','accounts','drives']

        if HAS_SF_SDK is False:
            self.module.fail_json(msg="Unable to import the SolidFire Python SDK")
        else:
            self.sfe = netapp_utils.create_sf_connection(module=self.module)

    def get_user_account_by_id(self):
	"""This function returns details about the account. None if not found.

        :param name:self.
        :type name: int.
        :returns:  int - if found. none - if not found.

        """
        list_accounts_result = self.sfe.list_cluster_admins()

        for account in list_accounts_result.cluster_admins:
            if self.account_id == account.cluster_admin_id:
        	return account

        return None

    def create_cluster_user(self):
        """This function creates a cluster user account under cluster admins.

        :raises: DuplicateUsername

        """
        try:
            self.sfe.add_cluster_admin(username=self.account_name,
				   password=self.account_password,
				   access=self.access,
				   accept_eula=True)

        except:
            err = get_exception()
            self.module.fail_json(msg="Error creating cluster user account %s " % (self.account_name),
                                  exception=str(err))

    def create_ldap_user(self):
        """This function creates an ldap  user account under cluster admins.

        :raises: DuplicateUsername

        """
        try:
            self.sfe.add_ldap_cluster_admin(username=self.account_name,
                                   access=self.access,
                                   accept_eula=True)

        except:
            err = get_exception()
            self.module.fail_json(msg="Error creating ldap user account %s " % (self.account_name),
                                  exception=str(err))

    def update_account(self):
        """This function modifies the cluster admins user accounts based on cluster admin id.

        :raises: Exception

        """
	try:
            self.sfe.modify_cluster_admin(cluster_admin_id=self.account_id,
				   password=self.account_password,
                                   access=self.access)

        except:
            err = get_exception()
            self.module.fail_json(msg="Error updating user account %s " % (self.account_id),
                                  exception=str(err))

    def delete_account(self):
	"""This function deletes the cluster admins user account based on cluster admins id

        :raises: Exception

        """
        try:
            self.sfe.remove_cluster_admin(cluster_admin_id=self.account_id)

        except:
            err = get_exception()
            self.module.fail_json(msg="Error deleting user account %s " % (self.account_id),
                                  exception=str(err))

    def apply(self):
	""" This function checks if user account exists or not.
        If exists, then deletes the duplicate user account
        if does not exists, then creates an user account based on type of the user
        """
        changed = False
        account_exists = False
        update_account = False
        account_detail = self.get_user_account_by_id()
        
        if account_detail:
            account_exists = True

            if self.state == 'absent':
                # Checking for state change(s) here, and applying it later in the code allows us to support
                # check_mode
                changed = True

            elif self.state == 'present':
                if account_detail.access is not None and self.access is not None and account_detail.access != self.access:
                    update_account = True
                    changed = True

                elif account_detail.cluster_admin_id is not None and self._accountid is not None \
                        and account_detail.cluster_admin_id != self.account_id:
                    update_account = True
                    changed = True
		
		elif account_detail.account_password is not None and self.account_password is not None \
			and account_detail.account_password != self.account_password:
                    update_account = True
                    changed = True

	else:
            if self.state == 'present':
                changed = True

        result_message = ""

        if changed:
            if self.module.check_mode:
                result_message = "Check mode, skipping changes"
                pass
            else:
                if self.state == 'present':
                    if not account_exists:
			if self.user_type == 'ldap':
                        	self.create_ldap_user() 
	                        result_message = "LDAP user account created"
			elif self.user_type == 'cluster': 
				self.create_cluster_user()
				result_message = "Cluster user account created"
		    else:
			self.update_account()
			result_message = "User account updated succesfully"

                elif self.state == 'absent':
                    self.delete_account()
                    result_message = "Account deleted successfully"

        self.module.exit_json(changed=changed, msg=result_message)

def main():
    v = SolidFireUserAccount()
    v.apply()

if __name__ == '__main__':
    main()

