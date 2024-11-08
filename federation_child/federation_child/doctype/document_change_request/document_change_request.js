// Copyright (c) 2024, ajay@mail.hybrowlabs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Document Change Request", {
	refresh(frm) {
            $(
                frappe.render_template("version_view", { doc: frm.doc, data: JSON.parse(frm.doc.data) })
            ).appendTo(frm.fields_dict.table_html.$wrapper.empty());
        
            frm.add_custom_button(__("Show all Versions"), function () {
                frappe.set_route("List", "Version", {
                    ref_doctype: frm.doc.ref_doctype,
                    docname: frm.doc.docname,
                });
            });
      
	},
});
