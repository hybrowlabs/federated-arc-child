import json
import frappe

#Generate Api Key And Secret
@frappe.whitelist(allow_guest=True)
def get_api_secret():
    user = frappe.get_doc('User', "Administrator")
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


#filter master List
@frappe.whitelist()
def get_master_list():
    master=frappe.get_doc("Master List")
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
