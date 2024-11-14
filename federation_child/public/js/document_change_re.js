
// Function to add a custom Document Change Request Button and Disable Save Dynamically
function addCustomButton(doctype) {
    frappe.ui.form.on(doctype, {
        refresh: function(frm) {
            frm.disable_save();
            frm.add_custom_button('Create Document Change Request', function() {
                frappe.call({
                    method: 'federation_child.api.document_change_request',
                    args:{
                        self:frm.doc
                    },
                    callback: function(r) {

                    }
                })
               
            });
        }
    });
}






frappe.call({
    method: 'federation_child.api.get_master_list',
    callback: function(r) {
        // List of target doctypes where the button should be added
        const doctypes = r.message;
        // Iterate over each target doctype and apply the button logic
        doctypes.forEach(doctype => {
            addCustomButton(doctype);
        });
        
    }
})