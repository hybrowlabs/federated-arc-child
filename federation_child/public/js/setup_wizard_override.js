frappe.provide("erpnext.setup");

//Override Erpnext Setup Wizard
(function() {
	// Remove specific slides by filtering out based on the slide name
	erpnext.setup.slides_settings = erpnext.setup.slides_settings.filter(slide => {
		return slide.name !== "organization";
	});

	const custom_slides = [
		
	];

	// Add custom slides if necessary
	erpnext.setup.slides_settings = [...erpnext.setup.slides_settings, ...custom_slides];
})();
