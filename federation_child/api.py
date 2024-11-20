import json
import frappe
from frappe.auth import LoginManager

#Generate Api Key And Secret
@frappe.whitelist()
def get_api_secret(user_id=None):
    if not user_id:
        user = frappe.get_doc('User', "Administrator")
    else:
        user=frappe.db.get_value("User",user_id,"name")
        if user:
            user = frappe.get_doc('User', user_id)
        else:
            frappe.throw(f'User {user_id} Not Found')

    api_secret = user.get_password('api_secret') if user.api_secret else None
    if not user.api_key:
        api_key = frappe.generate_hash(length=15)
        user.api_key = api_key
        user.save(ignore_permissions=True)
    if not api_secret:
        api_secret = frappe.generate_hash(length=15)
        user.api_secret = api_secret
        user.save(ignore_permissions=True)
    return str(user.api_key),str(api_secret)

#Get sid
@frappe.whitelist(methods=["GET"])
def get_cookies():
    user_id = frappe.session.user
    login_manager = LoginManager()
    login_manager.login_as(user_id)
    return {
        "user_id":user_id,
        "success": True
    }

#login With Sid
@frappe.whitelist(allow_guest=True)
def login_with_sid(sid,domain):
    frappe.session.sid=sid
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = str(domain)+"/app"

#filter master List
@frappe.whitelist()
def get_master_list():
    master=frappe.get_doc("Site Federation Config")
    master_list= [mas_doc.select_doctype for mas_doc in master.master_doctypes]
    return master_list


#Get Master Doctype Json
@frappe.whitelist()
def get_doctype_schema(doctype):
    doc=frappe.get_doc("DocType",doctype)
    return doc.as_dict().update({"module":"Custom"})


#Existing master record For Disallow Duplication
@frappe.whitelist()
def existing_record_list(doctype):
    records=frappe.get_all(doctype, pluck='name')
    return records



#Create master Doctype In Fedration
@frappe.whitelist()
def create_master_record(records):
    records=frappe.parse_json(records)
    for i in records:
        doc=frappe.get_doc(i)
        doc.insert()



#Document change Request Creation
@frappe.whitelist()
def document_change_request(self):
    self=json.loads(self)
    doc=frappe.get_doc(self.get("doctype"),self.get("name"))
    doc_to_compare = doc
    if not doc_to_compare and (amended_from := doc.get("amended_from")):
        doc_to_compare = frappe.get_doc(self.get("doctype"), amended_from)
    dcr = frappe.new_doc("Document Change Request")
    dcr.update_version_info(doc_to_compare, frappe._dict(self))
    dcr.new_data= frappe._dict(self)
    dcr.status="Pending"
    dcr.insert(ignore_permissions=True)




@frappe.whitelist()
def approve_change_request(name,status):
    doc=frappe.get_doc("Document Change Request",name)
    doc.status=status
    doc.save(ignore_permissions=True)
    if status=="Approved":
        new_doc=frappe.get_doc(doc.ref_doctype,doc.docname)
        new_doc.update(doc.new_data)
        new_doc.save(ignore_permissions=True)



@frappe.whitelist()
def create_social_login(client_id,client_secret,base_url):
    doc=frappe.new_doc("Social Login Key")
    doc.enable_social_login=1
    doc.social_login_provider="Frappe"
    doc.provider_name="Frappe"
    doc.client_id=client_id
    doc.client_secret=client_secret
    doc.base_url=base_url
    doc.authorize_url="/api/method/frappe.integrations.oauth2.authorize"
    doc.access_token_url="/api/method/frappe.integrations.oauth2.get_token"
    doc.redirect_url="/api/method/frappe.integrations.oauth2_logins.login_via_frappe"
    doc.api_endpoint="/api/method/frappe.integrations.oauth2.openid_profile"
    doc.auth_url_data='{"response_type": "code", "scope": "openid"}'
    doc.save(ignore_permissions=True)