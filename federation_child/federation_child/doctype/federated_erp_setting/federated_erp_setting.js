// Copyright (c) 2024, ajay@mail.hybrowlabs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Federated Erp Setting", {
	refresh(frm) {
        frm.add_custom_button(__('Create Site to Federated'), function() {
            frappe.call({
                method:"create_site_on_fedrated",
                doc:frm.doc,
                callback:function(r){

                }
            })
        })
	},
});
