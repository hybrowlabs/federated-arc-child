import json
from erpnext.setup.doctype.company.company import install_country_fixtures
from erpnext.setup.setup_wizard.operations.taxes_setup import setup_taxes_and_charges
import frappe
import requests

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
    master=frappe.get_doc("Site Federation Config")
    master_list= [mas_doc.select_doctype for mas_doc in master.master_doctypes]
    return master_list


#Get Master Doctype Json
@frappe.whitelist()
def get_doctype_schema(doctype):
    """
    Create Master Doctype Api In Fedration
    """
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
    """
    Creating Master Record In Child Api
    """
    records=frappe.parse_json(records)
    for record in records:
        fed_sett=frappe.get_doc("Federated Erp Setting")
        if record.get("item_defaults"):
            record.pop('item_defaults', None)
        if record.get("doctype")=="Company":
            url=f'{fed_sett.federated_site_name}/api/method/fedration_erp.fedration_erp.api.create_company_related_documents'
            payload=json.dumps({
                    "company":record.get("name")
                })
            api_secret =fed_sett.get_password(fieldname="api_secret_pass", raise_exception=False)
            headers = {
                'Content-Type': 'application/json',
                'Authorization':'token '+str(fed_sett.api_key)+":"+str(api_secret)
            }
            response = requests.request("Get", url, headers=headers,data=payload)
            if response.status_code==200:
                doc=None
                company_exist=frappe.db.exists("Company",{"name":record.get("name")})
                if not company_exist:
                    doc=frappe.new_doc("Company")
                    doc.abbr=record.get("abbr")
                    doc.company_name=record.get("company_name")
                    doc.default_currency=record.get("default_currency")
                    doc.country=record.get("country")
                    doc.enable_perpetual_inventory=record.get("enable_perpetual_inventory")
                    doc.save(ignore_permissions=True)
                    frappe.db.commit()
                else:
                    doc=frappe.get_doc("Company",record.get("name"))
                #Creating Account ,Warehouse, Department ,Cost center For company
                create_accounts_recursive(response.json().get("message").get("accounts"))
                create_warehouses_recursive(response.json().get("message").get("warehouse"))
                create_cost_centers_recursive(response.json().get("message").get("cost_center"))
                create_departments_recursive(response.json().get("message").get("department"))

                for key, value in record.items():
                    if key not in ["doctype", "name","modified","created_on","creation"]:
                        doc.set(key, value)
                doc.save(ignore_permissions=True)
                frappe.clear_cache()

                if frappe.flags.country_change:
                    install_country_fixtures(record.get("name"), record.get("country"))
                    create_default_tax_template(record.get("name"), record.get("country"))
                
                if not frappe.local.flags.ignore_chart_of_accounts:
                    if record.get("default_cash_account"):
                        set_mode_of_payment_account(record.get("name"),record.get("default_cash_account"))

                if record.get("default_currency"):
                    frappe.db.set_value("Currency", record.get("default_currency"), "enabled", 1)

                if (
                    hasattr(frappe.local, "enable_perpetual_inventory")
                    and record.get("name") in frappe.local.enable_perpetual_inventory
                ):
                    frappe.local.enable_perpetual_inventory[record.get("name")] = record.get("enable_perpetual_inventory")

                frappe.clear_cache()


        else:
            if record.get("company"):
                company=frappe.defaults.get_defaults()
                record.update({"company":company.get("company")})
            existing_doc=frappe.db.get_value(record.get("doctype"),record.get("name"),"name")
            if not existing_doc:
                doc=frappe.get_doc(record)
                doc.insert()
            else:
                doc=frappe.get_doc(record.get("doctype"),record.get("name"))
                for key, value in record.items():
                    if key not in ["doctype", "name","modified","created_on","creation"]:
                        doc.set(key, value)
                doc.save(ignore_permissions=True)


        frappe.db.set_value(doc.doctype,doc.name,"name",record.get("name"))
        frappe.db.commit()




@frappe.whitelist()
def document_change_request(self):
    """
    Document change Request Creation Api
    """
    self=json.loads(self)
    doc=frappe.get_doc(self.get("doctype"),self.get("name"))
    doc_to_compare = doc
    if not doc_to_compare and (amended_from := doc.get("amended_from")):
        doc_to_compare = frappe.get_doc(self.get("doctype"), amended_from)
    dcr = frappe.new_doc("Document Change Request")
    dcr.update_version_info(doc_to_compare, frappe._dict(self))
    dcr.new_data= frappe.parse_json(self)
    dcr.status="Pending"
    dcr.insert(ignore_permissions=True)



@frappe.whitelist()
def approve_change_request(name,status):
    """
    Approve Document change Request Creation Api
    """
    doc=frappe.get_doc("Document Change Request",name)
    doc.status=status
    if status=="Approved":
        new_doc=frappe.get_doc(doc.ref_doctype,doc.docname)
        for key, value in eval(doc.new_data).items():
            if key not in ["doctype", "name","company","modified","creation"]:  # Skip non-field keys
                new_doc.set(key, value)
        
        new_doc.save()
        frappe.db.commit()
        
    doc.save(ignore_permissions=True)



def create_account(account_rec,accounts):
    """
    Create accounts based on the parent-child structure in the list.
    """
    for account in accounts: 
        if account["parent_account"]==account_rec:
            account.update({"doctype":"Account"})
            existing_account = frappe.db.get_value("Account", {"company": account["company"], "name": account["name"]},"name")
            if not existing_account:
                # Prepare account data
                account_doc =frappe.get_doc(account)
                # Insert the account in ERPNext
                account_doc.flags.ignore_mandatory=1
                account_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                
                create_account(account.get("name"),accounts)


def create_accounts_recursive(accounts):
    """
    Create accounts based on the parent-child structure in the list.
    """
    for account in accounts:
        account.update({"doctype":"Account"})
        if account.get("is_group")==1  and not account.get("parent_account"):
            existing_account = frappe.db.get_value("Account", {"company": account["company"], "name": account["name"]},"name")
            if not existing_account:
                account_doc = frappe.get_doc(account)
                # Insert the account in ERPNext
                account_doc.flags.ignore_mandatory=1
                account_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                create_account(account.get("name"),accounts)



def create_warehouse(warehouse_rec,warehouses):
    """
    Recursively create warehouses in ERPNext with parent-child relationships.
    """
    for warehouse in warehouses: 
        if warehouse["parent_account"]==warehouse_rec:
            warehouse.update({"doctype":"Warehouse"})
            existing_warehouse= frappe.db.get_value("Warehouse", {"company": warehouse["company"], "name": warehouse["name"]},"name")
            if not existing_warehouse:
                # Prepare account data
                warehouse_doc =frappe.get_doc(warehouse)
                # Insert the account in ERPNext
                warehouse_doc.flags.ignore_mandatory=1
                warehouse_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                
                create_warehouse(warehouse.get("name"),warehouses)


def create_warehouses_recursive(warehouses):
    """
    Create warehouses based on the parent-child structure in the list.
    """
    for warehouse in warehouses:
        warehouse.update({"doctype":"Warehouse"})
        if warehouse.get("is_group")==1  and not warehouse.get("parent_warehouse"):
            existing_warehouse = frappe.db.get_value("Warehouse", {"company": warehouse["company"], "name": warehouse["name"]},"name")
            if not existing_warehouse:
                warehouse_doc = frappe.get_doc(warehouse)
                # Insert the account in ERPNext
                warehouse_doc.flags.ignore_mandatory=1
                warehouse_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                create_warehouse(warehouse.get("name"),warehouses)


def create_cost_center(cost_center_rec,cost_centers):
    """
    Recursively create warehouses in ERPNext with parent-child relationships.
    """
    for cost_center in cost_centers: 
        if cost_center["parent_account"]==cost_center_rec:
            cost_center.update({"doctype":"Cost Center"})
            existing_cost_center = frappe.db.get_value("Cost Center", {"company": cost_center["company"], "name": cost_center["name"]},"name")
            if not existing_cost_center:
                # Prepare account data
                cost_center_doc =frappe.get_doc(cost_centers)
                # Insert the account in ERPNext
                cost_center_doc.flags.ignore_mandatory=1
                cost_center_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                
                create_cost_center(cost_center.get("name"),cost_centers)


def create_cost_centers_recursive(cost_centers):
    """
    Create warehouses based on the parent-child structure in the list.
    """
    for cost_center in cost_centers:
        cost_center.update({"doctype":"Cost Center"})
        if cost_center.get("is_group")==1  and not cost_center.get("parent_cost_center"):
            existing_cost_center = frappe.db.get_value("Cost Center", {"company": cost_center["company"], "name": cost_center["name"]},"name")
            if not existing_cost_center:
                cost_center_doc = frappe.get_doc(cost_center)
                # Insert the account in ERPNext
                cost_center_doc.flags.ignore_mandatory=1
                cost_center_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                create_cost_center(cost_center.get("name"),cost_centers)


def create_department(department_rec,departments):
    """
    Recursively create warehouses in ERPNext with parent-child relationships.
    """
    for department in departments: 
        if department["parent_account"]==department_rec:
            department.update({"doctype":"Department"})
            existing_department = frappe.db.get_value("Cost Center", {"company": department["company"], "name": department["name"]},"name")
            if not existing_department:
                # Prepare account data
                department_doc =frappe.get_doc(departments)
                # Insert the account in ERPNext
                department_doc.flags.ignore_mandatory=1
                department_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                
                create_department(department.get("name"),departments)


def create_departments_recursive(departments):
    """
    Create warehouses based on the parent-child structure in the list.
    """
    for department in departments:
        department.update({"doctype":"Department"})
        if department.get("is_group")==1  and not department.get("parent_department"):
            existing_department= frappe.db.get_value("Department", {"company": department["company"], "name": department["name"]},"name")
            if not existing_department:
                department_doc = frappe.get_doc(department)
                # Insert the account in ERPNext
                department_doc.flags.ignore_mandatory=1
                department_doc.insert(ignore_if_duplicate=True)
                frappe.db.commit()
                create_department(department.get("name"),departments)


@frappe.whitelist()
def create_default_tax_template(name,country):
    """
    Sales Tax Charges Creation
    """
    setup_taxes_and_charges(name, country)


def set_mode_of_payment_account(name,default_cash_account):
    cash = frappe.db.get_value("Mode of Payment", {"type": "Cash"}, "name")
    if (
        cash
        and default_cash_account
        and not frappe.db.get_value("Mode of Payment Account", {"company": name, "parent": cash})
    ):
        mode_of_payment = frappe.get_doc("Mode of Payment", cash, for_update=True)
        mode_of_payment.append(
            "accounts", {"company": name, "default_account": default_cash_account}
        )
        mode_of_payment.save(ignore_permissions=True)