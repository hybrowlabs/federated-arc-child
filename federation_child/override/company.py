

import frappe
from erpnext.setup.doctype.company.company import Company, install_country_fixtures
from frappe.utils.nestedset import NestedSet



class CustomCompany(Company):
    """
    Override Company on_update Method For Company Creation From Federated
    """
    def on_update(self):
        if not self.get("__islocal"):
            NestedSet.on_update(self)
            if not frappe.db.sql(
                """select name from tabAccount
                    where company=%s and docstatus<2 limit 1""",
                self.name,
            ):
                if not frappe.local.flags.ignore_chart_of_accounts:
                    frappe.flags.country_change = True
                    self.create_default_accounts()
                    self.create_default_warehouses()

            if not frappe.db.get_value("Cost Center", {"is_group": 0, "company": self.name}):
                self.create_default_cost_center()

            if frappe.flags.country_change:
                install_country_fixtures(self.name, self.country)
                self.create_default_tax_template()

            if not frappe.db.get_value("Department", {"company": self.name}):
                self.create_default_departments()

            if not frappe.local.flags.ignore_chart_of_accounts:
                self.set_default_accounts()
                if self.default_cash_account:
                    self.set_mode_of_payment_account()

            if self.default_currency:
                frappe.db.set_value("Currency", self.default_currency, "enabled", 1)

            if (
                hasattr(frappe.local, "enable_perpetual_inventory")
                and self.name in frappe.local.enable_perpetual_inventory
            ):
                frappe.local.enable_perpetual_inventory[self.name] = self.enable_perpetual_inventory

            if frappe.flags.parent_company_changed:
                from frappe.utils.nestedset import rebuild_tree

                rebuild_tree("Company", "parent_company")

            frappe.clear_cache()