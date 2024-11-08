// Copyright (c) 2024, ajay@mail.hybrowlabs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Federated Erp Setting", {
	refresh(frm) {
        // if(!frm.doc.__islocal){
        //     frm.add_custom_button(__('Generate Api Secret'), function() {
        //         frappe.call({
        //             method:"get_api_key_secret",
        //             doc:frm.doc,
        //             callback:function(r){

        //             }
        //         })
        //     })
        // }
	},
});
