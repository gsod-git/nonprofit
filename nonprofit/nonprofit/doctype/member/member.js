// Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.ui.form.on('Member', {
    refresh: function(frm) {
        frm.set_query("newsletter", function() {
            return {
                "filters": {
                    "category": "Newsletter"
                }
            };
        });
        frm.set_query("samaj_darshan", function() {
            return {
                "filters": {
                    "category": "Samaj Darshan"
                }
            };
        });
        if(!frm.doc.primary_member_id && !frm.doc.self_relation){
            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    'doctype': "Relationship",
                    'filters': { 'is_member': "Yes" },
                    'fieldname': [
                        'name'
                    ]
                },
                callback: function(data) {
                    if (data.message) {
                        frm.set_value("self_relation", data.message.name);
                    }
                }
            });
        }            
        // frappe.call({
        //     method: "frappe.client.get_value",
        //     args: {
        //         'doctype': "Membership",
        //         'filters': { 'member': frm.doc.name },
        //         'order_by':'creation desc',
        //         'fieldname': [
        //             'to_date'
        //         ]
        //     },
        //     callback: function(data) {
        //         if (data.message) {
        //             frappe.model.set_value(frm.doctype, frm.docname,
        //                 "membership_expiry_date", data.message.to_date);
        //         }
        //     }
        // });
        frappe.call({
            method: "nonprofit.nonprofit.doctype.member.member.get_member_exipry_date",
            args: {
                member_id: frm.doc.name
            },
            callback: function(data) {
               if (data.message) {
                    frappe.model.set_value(frm.doctype, frm.docname,
                        "membership_expiry_date", data.message.to_date);
                }
            }
        });
        if(frm.doc.__islocal)
            frm.set_value('self_relation','Self')
        if(frm.doc.self_relation!="Self"){
            frm.toggle_display(['children'], false);
        }
    },
    phone_no: function(frm) {
        if (frm.doc.phone_no) {
            var regex = /[0-9]+$/;
            if (!regex.test(frm.doc.phone_no)) {
                frm.set_value("phone_no", '');
                frappe.throw('Please enter a valid mobile number')
            }
        }
    },
    home_phone_no: function(frm) {
        if (frm.doc.home_phone_no) {
            var regex = /[0-9]+$/;
            if (!regex.test(frm.doc.home_phone_no)) {
                frm.set_value("home_phone_no", '');
                frappe.throw('Please enter a valid home phone number')
            }
        }
    },
    mobile_no: function(frm) {
        if (frm.doc.mobile_no) {
            var regex = /[0-9]+$/;
            if (!regex.test(frm.doc.mobile_no)) {
                frm.set_value("mobile_no", '');
                frappe.throw('Please enter a valid whatsapp number')
            }
        }
    },
    office_no: function(frm) {
        if (frm.doc.office_no) {
            var regex = /[0-9]+$/;
            if (!regex.test(frm.doc.office_no)) {
                frm.set_value("office_no", '');
                frappe.throw('Please enter a valid office number')
            }
        }
    },
    email: function(frm) {
        if (frm.doc.email) {
            var regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
            if (!regex.test(frm.doc.email)) {
                frm.set_value("email", '');
                frappe.throw('Please enter a valid email id')
            }
        }
    },
    zip_code: function(frm) {
        if (frm.doc.zip_code) {
            var regex = /[0-9]+$/;
            if (!regex.test(frm.doc.zip_code)) {
                frm.set_value("zip_code", '');
                frappe.throw('Please enter a valid zip code')
            }
        }
    },
    state: function(frm) {
        if (frm.doc.state) {
            var regex = /[a-zA-Z ]+$/;
            if (!regex.test(frm.doc.state)) {
                frm.set_value("state", '');
                frappe.throw('Please enter a valid state name')
            }
        }
    }
});
frappe.ui.form.on("Member", "date_of_birth", function(frm, cdt, cdn) {
    if(frm.doc.self_relation){
        frappe.call({
            method: "nonprofit.nonprofit.doctype.member.member.get_relationgroup",
            args: {
                relation: frm.doc.self_relation
            },
            callback: function(r) {
                frm.set_value("member_group", r.message[0][0]);
                if (frm.doc.member_group) {
                    var today = new Date();
                    var birthDate = new Date(frm.doc.date_of_birth);
                    var age_str = get_age(frm.doc.date_of_birth);
                    frm.set_value("ageyears", age_str);
                    frappe.call({
                        method: "nonprofit.nonprofit.doctype.member.member.get_self_agelimit",
                        args: {
                            "age_limit": age_str,
                            "relation": frm.doc.member_group,
                            "parent": frm.doc.membership_type
                        },
                        callback: function(r) {
                            if (r.message[0].age_condition == "Minimum") {
                                var ages = r.message[0].age_limit;
                                var html = '<div>'
                                html += '<br><span style="float:left;margin-right: 10px;;">Member age should be above ' + ages + '</span><br/>'
                                html += '</div>'
                                frappe.msgprint(html, 'Member')
                            } else if (r.message[0].age_condition == "Maximum") {
                                var ages = r.message[0].age_limit;
                                var html = '<div>'
                                html += '<br><span style="float:left;margin-right: 10px;;">Member age should be below ' + ages + '</span><br/>'
                                html += '</div>'
                                frappe.msgprint(html, 'Member')
                            }
                        }
                    })
                }
            }
        });
    }
});

frappe.ui.form.on("Member", "membership_type", function(frm, cdt, cdn) {
    if (frm.doc.membership_type) {
        frappe.call({
            method: "nonprofit.nonprofit.doctype.member.member.get_rolecount",
            args: {
                "relation": frm.doc.membership_type
            },
            callback: function(r) {
                // $.each(r.message, function(i, d) {
                //     for (var i = 1; i <= d.allowed_members; i++) {
                //         var row = frappe.model.add_child(frm.doc, "Other Members", "table_25");
                //         row.relationship_group = d.relationship;
                //     }
                // });
                // refresh_field("table_25");
                // $('.grid-add-row').parent().parent().parent().hide();
            }
        });
        frm.set_value("membership", frm.doc.membership_type);
    }
});
frappe.ui.form.on("Member", "refresh", function(frm) {
    // cur_frm.fields_dict['table_25'].grid.get_field('relation').get_query = function(doc, cdt, cdn) {
    //     var d = locals[cdt][cdn];
    //     return {
    //         query: "nonprofit.nonprofit.doctype.member.member.add_relation",
    //         filters: {
    //             'relationship_group': d.relationship_group,
    //         }
    //     }
    // }
});
frappe.ui.form.on("Member", {
    refresh: function(frm) {
        date_ofbirth = []
        var relationg = frm.doc.membership_type;
        for (var i = 0; i < frm.doc.table_25.length; i++) {
            date_ofbirth = frm.doc.table_25[i].date_of_birth;
            relation = frm.doc.table_25[i].relation;
            relationship_group = frm.doc.table_25[i].relationship_group;
            if (date_ofbirth) {
                var today = new Date();
                var birthDate = new Date(date_ofbirth);
                var age_str = get_age(date_ofbirth);
                frappe.call({
                    method: "nonprofit.nonprofit.doctype.member.member.get_self_agelimit",
                    args: {
                        "age_limit": age_str,
                        "relation": relationship_group,
                        "parent": relation
                    },
                    callback: function(r) {
                        if (r.message[0].age_condition == "Minimum") {
                            var ages = r.message[0].age_limit;
                            var html = '<div>'
                            html += '<br><span style="float:left;margin-right: 10px;;">Family Member age should be above ' + ages + '</span><br/>'
                            html += '</div>'
                            frappe.msgprint(html, 'Member')
                        } else if (r.message[0].age_condition == "Maximum") {
                            var ages = r.message[0].age_limit;
                            var html = '<div>'
                            html += '<br><span style="float:left;margin-right: 10px;;">Family Member age should be below ' + ages + '</span><br/>'
                            html += '</div>'
                            frappe.msgprint(html, 'Member')
                        }
                        // if(r.message){
                        //    console.log(r.message)
                        // }
                        // else{
                        //     console.log(relationship_group)
                        //     frappe.throw(__("Age limit is exceed!"))
                        // }
                    }
                })
                // frm.set_value("age_years", age_str);
            }
        }
    }
});
var get_age = function(birth) {
    var ageMS = Date.parse(Date()) - Date.parse(birth);
    var age = new Date();
    age.setTime(ageMS);
    var years = age.getFullYear() - 1970;
    var newage = years;
    return newage
};
frappe.ui.form.on("Other Members", "email", function(frm, cdt, cdn) {
    var item = frappe.get_doc(cdt, cdn);
    var regex = /^([a-zA-Z0-9_.+-])+\@(([a-zA-Z0-9-])+\.)+([a-zA-Z0-9]{2,4})+$/;
    if (!regex.test(item.email)) {
        frappe.model.set_value(cdt, cdn, "email", "");
        frappe.throw('Please enter a valid email id at Row ' + item.idx)
    }
});
frappe.ui.form.on("Other Members", "phone_no", function(frm, cdt, cdn) {
    var item = frappe.get_doc(cdt, cdn);
    var regex = /[0-9]+$/;
    if (!regex.test(item.phone_no)) {
        frappe.model.set_value(cdt, cdn, "phone_no", "");
        frappe.throw('Please enter a valid phone no at Row ' + item.idx)
    }
});
frappe.ui.form.on("Other Members", "relation", function(frm, cdt, cdn) {
    var item = frappe.get_doc(cdt, cdn);
    frappe.call({
        method: "nonprofit.nonprofit.doctype.member.member.get_relationgroup",
        args: {
            relation:item.relation
        },
        callback: function(data) {
            if (data.message) {
                frappe.model.set_value(cdt, cdn, "relationship_group", data.message[0].parent);
            }
        }
    })
});