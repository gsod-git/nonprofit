// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Membership', {
    refresh: function(frm) {
        frm.set_query("accounting_head", function() {
            return {
                "filters": {
                    "accounting_group": frm.doc.accounting_group
                }
            };
        });
    },
    onload: function(frm) {
        frm.add_fetch('membership_type', 'amount', 'amount');
        var name = ''
        if (frm.doc.docstatus == 1) {
            frappe.call({
                method: 'gscommunity.gscommunity.doctype.payment_entries.payment_entries.get_payment_entry',
                args: {
                    'doctype': frm.doctype,
                    'ref_id': frm.doc.name
                },
                callback: function(data) {
                    if (data.message != undefined) {
                        name = data.message[0].name;
                        frm.add_custom_button(__('View Payment Entry'), function() {
                            frappe.set_route("Form", "Payment Entries", name);
                        });
                    } else {
                        frm.add_custom_button(__('Make Payment Entry'), function() {
                            frappe.set_route("Form", "Payment Entries", "New Payment Entries", {
                                has_reference: 1,
                                payment_for: frm.doctype,
                                ref_id: frm.doc.name,
                                paid_amount: frm.doc.amount,
                                member: frm.doc.member,
                                accounting_head: frm.doc.accounting_head,
                                payment_type: 'Credit'
                            });
                        });
                    }
                }
            })
        }
    }
});

frappe.ui.form.on("Membership", "membership_type", function(frm, cdt, cdn) {

    frappe.call({
        method: "gscommunity.gscommunity.doctype.general_settings.general_settings.get_validity",
        args: {
            "membershiptype": frm.doc.membership_type
        },
        callback: function(r) {
            var t = r.message;
            if (t) {
                if (t.membership_type == frm.doc.membership_type) {
                    var aYearFromNow = new Date();
                    console.log(aYearFromNow.getFullYear() + parseInt(t.validity))
                    aYearFromNow.setFullYear(aYearFromNow.getFullYear() + parseInt(t.validity));
                    console.log(aYearFromNow)
                    frm.set_value("to_date", aYearFromNow);
                } else {
                    frm.set_value("to_date", t.expiry_date);
                }
            }
        }
    })

});

frappe.ui.form.on("Membership", "paid", function(frm, cdt, cdn) {
    if (frm.doc.paid == "1") {

        frm.set_value("member_since_date", frappe.datetime.nowdate());
    }

});