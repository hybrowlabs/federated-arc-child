# Copyright (c) 2024, ajay@mail.hybrowlabs.com and contributors
# For license information, please see license.txt

import json
from federation_child.api import get_api_secret
import frappe
from frappe.model.document import Document
import requests

from frappe.utils import cstr, get_site_name, get_site_url


class FederatedErpSetting(Document):
	def before_save(self):
		if self.federated_site_name and self.site_created==0:
			self.create_site_on_fedrated()


	@frappe.whitelist()
	def create_site_on_fedrated(self):
		"""
			Create Site On Fedrated
		"""
		api=get_api_secret()
		url=f'{self.federated_site_name}/api/method/fedration_erp.fedration_erp.api.create_site'
		payload=json.dumps({
				"site_name" : get_site_url(get_site_name(frappe.local.request.host)),
				"api_key":api[0],
				"api_secret":api[1]
			})
		api_secret =self.get_password(fieldname="api_secret_pass", raise_exception=False)
		headers = {
			'Content-Type': 'application/json',
			'Authorization':'token '+str(self.api_key)+":"+str(api_secret)
		}
		response = requests.request("Post", url, headers=headers,data=payload)
		if response.status_code!=200:
			frappe.log_error(title = 'Site creation error',message=response.text)
			frappe.msgprint("Failed To Create Site")
		else:
			frappe.db.set_single_value("Federated Erp Setting", "site_created", 1)
			frappe.msgprint("Site Created Sucessfully")