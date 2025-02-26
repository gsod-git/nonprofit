# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, nowdate, getdate
# from frappe import _
from datetime import date


class Membership(Document):
	def validate(self):
		member_name = frappe.get_value('Member', dict(email=frappe.session.user))

		# if not member_name:
		# 	user = frappe.get_doc('User', frappe.session.user)
		# 	member = frappe.get_doc(dict(
		# 		doctype='Member',
		# 		email=frappe.session.user,
		# 		membership_type=self.membership_type,
		# 		member_name=user.get_fullname()
		# 	)).insert(ignore_permissions=True)
		# 	member_name = member.name

		# if self.get("__islocal"):
		# 	self.member = member_name


		# get last membership (if active)
		# last_membership = erpnext.get_last_membership()

		# if person applied for offline membership
		# if last_membership and not frappe.session.user == "Administrator":
			# if last membership does not expire in 30 days, then do not allow to renew
			# if getdate(add_days(last_membership.to_date, -30)) > getdate(nowdate()):
			# 	frappe.throw(_('You can only renew if your membership expires within 30 days'))

		# 	self.from_date = add_days(last_membership.to_date, 1)
		# elif frappe.session.user == "Administrator":
		# 	self.from_date = self.from_date
		# else:
		# 	self.from_date = nowdate()

		# self.to_date = add_years(self.from_date, 1)
		calculate_expiry(self)

	def on_payment_authorized(self, status_changed_to=None):
		if status_changed_to in ("Completed", "Authorized"):
			self.load_from_db()
			self.db_set('paid', 1)

	def on_submit(self):	
		member=frappe.get_doc('Member',self.member)
		update_family_members(self.member,self.membership_type,1,self.to_date,self.amount)
		if member.primary_member_id:
			update_family_members(member.primary_member_id,self.membership_type,1,self.to_date,self.amount)
		family=frappe.db.sql('''select name,email from `tabMember` where (primary_member_id=%(member)s or primary_member_id=%(primary)s)''',{'member':self.member,'primary':member.primary_member_id},as_dict=1)
		if family:
			for x in family:
				update_family_members(x.name,self.membership_type,1,self.to_date,self.amount)
		

@frappe.whitelist()
def update_family_members(member,mem_type,active,exp_date,amount):
	if frappe.db.get_value('Member',member):
		doc=frappe.get_doc('Member',member)
		doc.membership_type=mem_type
		doc.active=active
		doc.membership_expiry_date=exp_date
		doc.membership_amount=amount
		doc.save(ignore_permissions=True)				

@frappe.whitelist()
def calculate_expiry(self):
	now=getdate(nowdate())
	settings=frappe.get_single('General Settings')
	expiry_date=settings.expiry_date
	if settings.membership_type==self.membership_type:
		expiry_date=date(int(now.year)+int(settings.validity),now.month,now.day)
	self.to_date=expiry_date

@frappe.whitelist(allow_guest=True)
def make_payment(docname,email,amount,membershiptype,transaction_id='',payment_date=None):
	member=frappe.db.get_all('Member',fields=['name','membership_type','membership_amount'],filters={'name':docname})
	if member:
		membership_type=frappe.db.get_all('Membership Type',fields=['validity','accounting_head'],filters={'name':member[0].membership_type})
		settings=frappe.get_doc('General Settings','General Settings')
		expiry_date=settings.expiry_date
		lifetime=settings.membership_type
		if member[0].membership_type==lifetime:
			now=getdate(nowdate()) if not payment_date else payment_date
			expiry_date=date(now.year+int(settings.validity),now.month,now.day)
		status='New'
		if frappe.db.get_value("Membership", member[0].name):
			status='Current'
		frappe.get_doc({
			"doctype": "Membership",
			"membership_type": membershiptype,
			"membership_status": status,
			"from_date": payment_date if payment_date else getdate(nowdate()),
			"member": member[0].name,
			"to_date":expiry_date,
			"amount":amount,
			"docstatus":1,
			"accounting_head":membership_type[0].accounting_head,
			"paid":1
		}).insert()
		docnames=frappe.db.get_all('Membership',fields=['name'],filters={'member':member[0].name},order_by='creation desc')
		if docnames:
			if not frappe.db.get_value("Payment Entries", docnames[0].name):
				frappe.get_doc({
					"doctype": "Payment Entries",
					"payment_date": payment_date if payment_date else getdate(nowdate()),
					"payment_for": "Membership",
					"ref_id": docnames[0].name,
					"member": member[0].name,
					"paid_amount":amount,
					"mode_of_payment":"Online Payment",
					"accounting_head":membership_type[0].accounting_head,
					"docstatus":1,
					"transaction_id":transaction_id,
					"payment_type":"Credit"
				}).insert()
		if frappe.db.get_value("Member", member[0].name):	
			frappe.db.set_value("Member", member[0].name , "active", 1)
			frappe.db.set_value("Member", member[0].name , "membership_type", membershiptype)
			family=frappe.db.get_all('Member',fields=['email','name'],filters={'primary_member_id':member[0].name})
			if family:
				for x in family:
					if frappe.db.get_value("Member", x.name):
						frappe.db.set_value("Member", x.name , "active", 1)
						frappe.db.set_value("Member", x.name , "membership_type", membershiptype)
