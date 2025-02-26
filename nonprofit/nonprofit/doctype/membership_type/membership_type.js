// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Membership Type', {
	refresh: function() {

	},

});

frappe.ui.form.on("Members Validation", {

	allowed_members: function(frm) {
		
		var total_amount = 0;
		for(var i=0;i<frm.doc.tab_11.length;i++) {
			total_amount += frm.doc.tab_11[i].allowed_members;
		}
		frm.set_value("count", total_amount);
	}
});