# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _, scrub
from frappe.model.document import Document
from frappe.contacts.address_and_contact import load_address_and_contact
from frappe.utils import getdate, add_months, add_to_date, nowdate, today, now
from frappe.desk.reportview import get_match_cond, get_filters_cond
import datetime
from datetime import date, datetime, time,timedelta


class Member(Document):
	def onload(self):
		load_address_and_contact(self)
		if self.membership_expiry_date:
			newdate1=date.today()
			newdate2=getdate(self.membership_expiry_date)
			if newdate1 > newdate2:
				frappe.msgprint(frappe._("Membership is Expired!").format())
			
	def validate(self):
		if self.email:
			self.validate_email_type(self.email)
		validate_zip(self.zip_code)
		# validate_memberage(self)
		if not self.primary_member_id:
			validate_age(self)
		if self.email:
			Emember=frappe.db.sql('''select * from `tabMember` where email=%(email)s and name!=%(name)s''',{'email':self.email,'name':self.name})
			if Emember:
				frappe.throw(_("{0} is already a member!").format(self.email))

	def validate_email_type(self, email):
		from frappe.utils import validate_email_address
		validate_email_address(email.strip(), True)
		
	def on_update(self):
		add_user(self)		
		if self.membership_expiry_date:
			newdate1=date.today()
			newdate2=getdate(self.membership_expiry_date)
			if newdate1 > newdate2:
				frappe.msgprint(frappe._("Membership is Expired!").format())
		rowcount=len(self.get('table_25'))
		validation=frappe.db.get_all('Members Validation',fields=['*'],filters={'parent':self.membership_type})
		allowed=0
		for item in validation:
			allowed=allowed+item.allowed_members
		# if(len(self.get('table_25'))>allowed):
		# 	frappe.throw(_('Only {0} family members can be added for {1}').format(allowed,self.membership_type))
		# validation=frappe.db.get_all('Members Validation',fields=['relationship','allowed_members','age_limit','parent'], filters={'parent':self.membership_type})
		validation=frappe.db.sql('''select v.relationship,v.allowed_members,v.age_limit,v.parent,
			v.is_depend_on,v.depends_on from `tabMembers Validation` v,`tabMembers Validation` v2 
			where v2.depends_on<>v.relationship and v.is_depend_on=0 and v.parent=%(parent)s''',
			{'parent':self.membership_type},as_dict=1)
		for item in validation:
			count=0		
			for member in self.table_25:
				if item.relationship==member.relationship_group:
					count=count+1
			if count>item.allowed_members:
				frappe.throw(_('You can add only {0} {1}').format(item.allowed_members,item.relationship))
		depended_validation=frappe.db.sql('''select v.relationship,v.allowed_members,v.age_limit,v.parent,
			v.is_depend_on,v.depends_on from `tabMembers Validation` v,`tabMembers Validation` v2 
			where (v2.depends_on=v.relationship or v.is_depend_on=1) and v.parent=%(parent)s group by v.name''',
			{'parent':self.membership_type},as_dict=1)
		if depended_validation:
			total_count=sum(x.allowed_members for x in depended_validation)
			for it in depended_validation:
				if it.is_depend_on:
					count=0
					for member in self.table_25:
						if it.depends_on==member.relationship_group or it.relationship==member.relationship_group:
							count=count+1
					if count>total_count:
						frappe.throw(_('You can add {0} or {1} together as {2} members in total').format(it.depends_on,it.relationship,total_count))
		add_ChildUser(self)
		check_child_member_status(self)
		# if self.email:
		# 	check_subscription(self)
		# check_current_membership(self)
		# print(self.recurring_payment)
		# if self.recurring_payment=="1":
		# 	from gscommunity.templates.pages.braintreepayment import insert_customer
		# 	insert_customer(self)

	def on_trash(self):
		frappe.db.sql('''delete from __global_search where name=%(name)s and doctype="Member"''',{'name':self.name})
		if self.primary_member_id:
			frappe.db.sql('''delete from `tabOther Members` where parent=%(parent)s and member_name=%(member_name)s and date_of_birth=%(dob)s''',
				{'parent':self.primary_member_id,'member_name':self.member_name,'dob':self.date_of_birth})
		user=frappe.db.get_all('User',filters={'username':self.name})
		new_email=self.name.lower()+"@gsod.org"
		if user:
			if user[0].name==new_email:
				frappe.delete_doc('User',user[0].name)
			else:
				frappe.db.set_value('User',user[0].name,'username',user[0].name)
		
		
@frappe.whitelist()
def add_parentrole(self,email):
	role=frappe.db.get_all('Has Role',filters={'parent':email,'role':'Member'})
	if not role:
		result= frappe.get_doc({
			"doctype": "Has Role",
			"name": nowdate(),
			"parent": email,
			"parentfield": "roles",
			"parenttype": "User",
			"role": "Member"
			}).insert(ignore_permissions=True)
		return result

	# def validate_relationship(self):
	# 	for d in self.get('table_25'):
	# 		if d.relation:
	# 			frappe.db.set_value("Other Members", d.email , "member_name", d.member_name)

@frappe.whitelist(allow_guest=True)
def add_user(self):	
	new_email=self.name.lower()+"@gsod.org"
	user_detail=frappe.db.get_all('User',filters={'username':self.name},fields=['name','email'])
	if not user_detail:		
		if self.email:
			user_d=frappe.db.get_all('User',filters={'name':self.email})
			if not user_d:
				insert_user(self,self.email,1)
			else:
				update_user(self,self.email)
		else:
			insert_user(self,new_email,0)
	else:
		if user_detail[0].email==new_email:
			if self.email:
				frappe.delete_doc('User',user_detail[0].name)
				insert_user(self,self.email,1)
			else:
				update_user(self,new_email)
		else:
			update_user(self,self.email)	
	if self.email:
		if self.newsletter:
			add_newsletter(self.newsletter,self.email)
		if self.samaj_darshan and not self.primary_member_id:
			add_newsletter(self.samaj_darshan,self.email)

@frappe.whitelist(allow_guest=True)
def update_user(self,email):
	if email:
		add_parentrole(self,email)
	frappe.db.set_value("User", email , "first_name", self.member_name)
	if self.phone_no:
		frappe.db.set_value("User", email , "mobile_no", self.phone_no)
	# frappe.db.set_value("User", email , "email", self.email)
	frappe.db.set_value("User", email , "username", self.name)
	frappe.db.set_value("User", email , "middle_name", self.middle_name)
	frappe.db.set_value("User", email , "last_name", self.last_name)
	frappe.db.set_value("User", email , "phone", self.home_phone_no)
	frappe.db.set_value("User", email , "gender", self.gender)
	frappe.db.set_value("User", email , "birth_date", self.date_of_birth)
	frappe.db.set_value("User", email , "location", self.state)
	
@frappe.whitelist(allow_guest=True)
def insert_user(self,email,send_mail):
	result= frappe.get_doc({
		"doctype": "User","email": email,"username":self.name,"first_name": self.member_name,
		"mobile_no":self.phone_no,"send_welcome_email":send_mail,"middle_name":self.middle_name,
		"last_name":self.last_name,"gender":self.gender,"phone":self.home_phone_no,
		"birth_date":self.date_of_birth,"location":self.state
	}).insert(ignore_permissions=True)
	add_parentrole(self,email)

@frappe.whitelist()
def validate_zip(zip_code):
	if len(str(zip_code)) > 5:
		frappe.throw(_("Zip code must contain 5 numbers").format(), frappe.PermissionError)
  
@frappe.whitelist()
def validate_memberage(self):
	now=datetime.now()
	birth=getdate(self.date_of_birth)
	age=now.year - birth.year - ((now.month, now.day) < (birth.month, birth.day))
	self.ageyears=age
	if self.self_relation:
		relation_group=frappe.db.get_all('Relations',filters={'relationship':self.self_relation},fields=['parent'])
		if relation_group:
			condition = ""
			Cond =frappe.db.sql("""select relationship, allowed_members, age_condition, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""".format(condition), 
								{"relation":relation_group[0].parent,"parent":self.membership_type}, as_dict=1)
			if Cond:
				if Cond[0].age_condition =="Maximum":
					Employee = frappe.db.sql("""select relationship, allowed_members, age_condition, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s and age_limit <= %(age_limit)s""".format(condition), 
								{"relation":relation_group[0].parent,"parent":self.membership_type,"age_limit":age}, as_dict=1)					
					if len(Employee) > 0:
						limit = frappe.db.sql("""select age_condition,age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""".format(condition), 
								{"relation":relation_group[0].parent,"parent":self.membership_type}, as_dict=1)	
						if limit:
							frappe.throw(_("Member age should be below {0}").format(limit[0].age_limit), frappe.PermissionError)	
						
				elif Cond[0].age_condition =="Minimum":
					Employee = frappe.db.sql("""select relationship, allowed_members, age_limit,age_condition from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s and age_limit >= %(age_limit)s""".format(condition), 
								{"relation":relation_group[0].parent,"parent":self.membership_type,"age_limit":age}, as_dict=1)					
					if len(Employee) > 0:
						limit = frappe.db.sql("""select age_condition,age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""".format(condition), 
								{"relation":relation_group[0].parent,"parent":self.membership_type}, as_dict=1)	
						if limit:						
							frappe.throw(_("Member age should be above {0}").format(limit[0].age_limit), frappe.PermissionError)				
			
@frappe.whitelist()
def validate_age(self):
	now=datetime.now()
	valid=[]
	relationgroup=[]
	if self.self_relation:
		self_age=now.year - getdate(self.date_of_birth).year - ((now.month, now.day) < (getdate(self.date_of_birth).month, getdate(self.date_of_birth).day))
		relation_group=frappe.db.get_all('Relations',filters={'relationship':self.self_relation},fields=['parent'])
		if relation_group:
			Cond =frappe.db.sql("""select relationship, allowed_members, allow_one, age_condition, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""", 
								{"relation":relation_group[0].parent,"parent":self.membership_type}, as_dict=1)
			if Cond:												
				if Cond[0].age_condition=='Minimum' and self_age<int(Cond[0].age_limit):
					err_msg="Age of {0} {1} should be above {2}".format(self.member_name,self.last_name,Cond[0].age_limit)
					if Cond[0].allow_one:
						valid.append({'relationship':Cond[0].relationship,'member_name':self.member_name,'success':0,'err_msg':err_msg})
					else:
						frappe.throw(frappe._('{0}').format(err_msg))
				elif Cond[0].age_condition=='Maximum' and self_age>int(Cond[0].age_limit):
					err_msg="Age of {0} {1} should be below {2}".format(self.member_name,self.last_name,Cond[0].age_limit)
					if Cond[0].allow_one:
						valid.append({'relationship':Cond[0].relationship,'member_name':self.member_name,'success':0,'err_msg':err_msg})
					else:
						frappe.throw(frappe._('{0}').format(err_msg))
				else:					
					if Cond[0].allow_one:
						valid.append({'relationship':Cond[0].relationship,'member_name':self.member_name,'success':1})
				if not Cond[0].relationship in relationgroup:
					relationgroup.append(Cond[0].relationship)

	if self.table_25:
		for item in self.table_25:
			age=now.year - getdate(item.date_of_birth).year - ((now.month, now.day) < (getdate(item.date_of_birth).month, getdate(item.date_of_birth).day))
			relation_group=frappe.db.get_all('Relations',filters={'relationship':item.relation},fields=['parent'])
			if relation_group:
				Cond =frappe.db.sql("""select relationship, allowed_members, allow_one, age_condition, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""", 
								{"relation":relation_group[0].parent,"parent":self.membership_type}, as_dict=1)
				if Cond:
					if Cond[0].age_condition=='Minimum' and age<int(Cond[0].age_limit):
						err_msg="Age of {0} {1} should be above {2}".format(item.member_name,item.last_name,Cond[0].age_limit)
						if Cond[0].allow_one:
							valid.append({'relationship':Cond[0].relationship,'member_name':item.member_name,'success':0,'err_msg':err_msg})
						else:
							frappe.throw(frappe._('{0}').format(err_msg))
					elif Cond[0].age_condition=='Maximum' and age>int(Cond[0].age_limit):
						err_msg="Age of {0} {1} should be below {2}".format(item.member_name,item.last_name,Cond[0].age_limit)
						if Cond[0].allow_one:
							valid.append({'relationship':Cond[0].relationship,'member_name':item.member_name,'success':0,'err_msg':err_msg})
						else:
							frappe.throw(frappe._('{0}').format(err_msg))
					else:					
						if Cond[0].allow_one:
							valid.append({'relationship':Cond[0].relationship,'member_name':item.member_name,'success':1})
							if not Cond[0].relationship in relationgroup:
								relationgroup.append(Cond[0].relationship)					
	if relationgroup:
		for item in relationgroup:
			exists=list(filter(lambda x: x['relationship'] == item, valid))
			if exists:
				success=list(filter(lambda x: x['success'] == 1, valid))
				if not len(success)>=1:
					fails=list(filter(lambda x: x['success'] == 0, valid))
					members=''
					err=''
					for li in fails:
						members+=li['member_name']+','
						err=li['err_msg'].split('should')[1]
					if len(fails)>1:
						frappe.throw(frappe._('Any of the members should {0}. The members are {1}').format(err,members[:-1]))
					else:
						frappe.throw(frappe._('{0}').format(fails[0]['err_msg']))

@frappe.whitelist()
def add_ChildUser(self):
	for d in self.get('table_25'):
		Teams=frappe.db.get_all('Member',fields=['name'],filters={'primary_member_id':self.name,'member_name':d.member_name,'date_of_birth':d.date_of_birth})
		if not Teams:
			result= frappe.get_doc({
				"doctype":"Member","member_name":d.member_name,"email":d.email,"phone_no":d.phone_no,
				"membership_type":self.membership_type,"address_line_1":self.address_line_1,
				"address_line_2":self.address_line_2,"city":self.city,"zip_code":self.zip_code,
				"state":self.state,"last_name":d.last_name,"gender":d.gender,"date_of_birth":d.date_of_birth,
				"newsletter":d.newsletter,"membership_expiry_date":self.membership_expiry_date,
				"active":self.active,"self_relation":d.relation,"primary_member_id":self.name,
				"membership_amount":self.membership_amount
			}).insert()						
		else:
			member=frappe.db.get_all('Member',fields=['*'],filters={'primary_member_id':self.name,'member_name':d.member_name,'date_of_birth':d.date_of_birth})
			if member:	
				doc = frappe.get_doc("Member", member[0].name)
				doc.member_name=d.member_name
				doc.last_name=d.last_name
				doc.gender=d.gender
				doc.date_of_birth=d.date_of_birth
				doc.email=d.email
				doc.phone_no=d.phone_no
				doc.primary_member_id=self.name
				doc.self_relation=d.relation
				doc.membership_type=self.membership_type
				doc.active=self.active
				doc.membership_expiry_date=self.membership_expiry_date
				doc.membership_amount=self.membership_amount
				doc.save()
			add_user(member[0])
			
@frappe.whitelist()
def add_ChildSubscriber(self):
	for d in self.get('table_25'):
		if d.email and d.newsletter:
			gmember= frappe.db.get_all('Email Group Member',fields=['name','email','email_group'],filters={'email':d.email})
			if gmember:
				if not frappe.db.get_value("Email Group Member", gmember[0].name) and d.newsletter:					
					result= frappe.get_doc({
						"doctype":"Email Group Member",
						"email_group":d.newsletter,
						"email":d.email
					}).insert(ignore_permissions=True)
					return result

@frappe.whitelist()
def add_relationgroup(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('relation'):
		return frappe.db.sql("""select parent from `tabRelations`
			where  relationship = %(relation)s and parent like %(txt)s {match_cond}
			order by
				if(locate(%(_txt)s, parent), locate(%(_txt)s, parent), 99999),
				idx desc,
				`tabRelations`.parent asc
			limit {start}, {page_len}""".format(
				match_cond=get_match_cond(doctype),
				start=start,
				page_len=page_len), {
					"txt": "%{0}%".format(txt),
					"_txt": txt.replace('%', ''),
					"relation": filters['relation']
				})

@frappe.whitelist(allow_guest=True)
def get_relationgroup(relation):
	if relation:
		return frappe.db.sql("""select parent from `tabRelations`
			where  relationship = %s""",relation,as_dict=1)

@frappe.whitelist(allow_guest=True)
def get_rolecount(relation):
	if relation:
		Group = frappe.db.get_all('Members Validation',fields=['relationship','allowed_members','age_limit'], filters={'parent':relation})
		return Group

@frappe.whitelist(allow_guest=True)
def get_roles(relation,cname):
	Group = frappe.db.get_all('Relations',fields=['relationship','parent'], filters={'relationship':relation})
	for item in Group:
		if frappe.db.get_value("Other Members", cname):	
			frappe.db.set_value("Other Members", cname , "relationship_group", item.parent)
	return Group
	 
# @frappe.whitelist(allow_guest=True)
# def validate_membercount(self):
# 	for d in self.get('table_25'):
# 	    if d.parent:
# 	        Group = frappe.db.get_all('Members Validation',fields=['relationship','allowed_members','age_limit'], filters={'parent':relation})	
# 			for g in Group:
#                  var row = frappe.model.add_child(frm.doc, "Other Members", "table_25");
#               row.relationship_group = d.relationship;
			 
# 			frappe.db.set_value("Other Members", cname , "relationship_group", item.parent)
# 	return Group	

@frappe.whitelist(allow_guest=True)
def get_age_limit(age_limit,relation,parent):
	# Group = frappe.db.get_all('Members Validation',fields=['relationship','allowed_members','age_limit'], filters={'parent':relation})
	# return Group
	condition = ""

	Employee = frappe.db.sql("""select relationship, age_condition, allowed_members, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s and age_limit >= %(age_limit)s""".format(condition), 
				{"relation":relation,"parent":parent,"age_limit":age_limit}, as_dict=1)	
	return Employee


@frappe.whitelist(allow_guest=True)
def get_self_agelimit(age_limit,relation,parent):
	condition = ""
	Cond =frappe.db.sql("""select relationship, allowed_members, age_condition, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""".format(condition), 
						{"relation":relation,"parent":parent}, as_dict=1)
	if Cond:
		if Cond[0].age_condition =="Maximum":
			Employee = frappe.db.sql("""select relationship, allowed_members, age_condition, age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s and age_limit <= %(age_limit)s""".format(condition), 
						{"relation":relation,"parent":parent,"age_limit":age_limit}, as_dict=1)	
				
			if len(Employee) > 0:

				limit = frappe.db.sql("""select age_condition,age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""".format(condition), 
						{"relation":relation,"parent":parent}, as_dict=1)	
					
				return limit
			else:
				limit ="Falsee"
				return limit
		elif Cond[0].age_condition =="Minimum":
			Employee = frappe.db.sql("""select relationship, allowed_members, age_limit,age_condition from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s and age_limit >= %(age_limit)s""".format(condition), 
						{"relation":relation,"parent":parent,"age_limit":age_limit}, as_dict=1)	
				
			if len(Employee) > 0:

				limit = frappe.db.sql("""select age_condition,age_limit from `tabMembers Validation` where relationship=%(relation)s and parent=%(parent)s""".format(condition), 
						{"relation":relation,"parent":parent}, as_dict=1)	
					
				return limit
			else:
				limit ="Falses"
				return limit

@frappe.whitelist(allow_guest=True)
def add_relation(doctype, txt, searchfield, start, page_len, filters):
	if filters.get('relationship_group'):
		return frappe.db.sql("""select relationship from `tabRelations`
			where  parent = %(relationship_group)s and relationship like %(txt)s and relationship !="Self" {match_cond}
			order by
				if(locate(%(_txt)s, relationship), locate(%(_txt)s, relationship), 99999),
				idx desc,
				`tabRelations`.relationship asc
			limit {start}, {page_len}""".format(
				match_cond=get_match_cond(doctype),
				start=start,
				page_len=page_len), {
					"txt": "%{0}%".format(txt),
					"_txt": txt.replace('%', ''),
					"relationship_group": filters['relationship_group']
				})

@frappe.whitelist(allow_guest=True)
def getage(birth):
	# ageMS = getdate(today()- birth)
	date_format = "%Y-%m-%d"
	a = datetime.strptime(today(), date_format)
	b = datetime.strptime(birth, date_format)
	ageMS = a - b
	age =datetime.now()
	# x = datetime.datetime.now()
	age.setTime(ageMS)
	frappe.msgprint(frappe._("{0}").format(age))
	# age.timedelta(ageMS)
	# years = age.getFullYear() - 1970
	
	# return years

@frappe.whitelist(allow_guest=True)
def add_newsletter(emailgroup,email):
	user_email=frappe.db.get_all('Email Group Member',fields=['email'],filters={'email':email,'email_group':emailgroup})
	if not user_email:
		result= frappe.get_doc({
		"doctype": "Email Group Member",
		"email_group": emailgroup,
		"email": email
		}).insert(ignore_permissions=True)
	subscribers=frappe.db.get_all('Email Group Member',fields=['name'],filters={'email_group':emailgroup})
	if frappe.db.get_value("Email Group", emailgroup):	
		frappe.db.set_value("Email Group", emailgroup , "total_subscribers", len(subscribers))
		
@frappe.whitelist(allow_guest=True)
def check_current_membership(self):
	membership=frappe.db.get_all('Membership',fields=['membership_type'],filters={'member':self.name},order_by='creation desc')
	if membership:
		self.membership_type=membership[0].membership_type

@frappe.whitelist(allow_guest=True)
def check_child_member_status(self):
	child_members=frappe.db.get_all('Member',filters={'primary_member_id':self.name},fields=['*'])
	if child_members:
		for item in child_members:
			child=frappe.db.get_all('Other Members',filters={'parent':self.name,'member_name':item.member_name,'date_of_birth':item.date_of_birth})
			if not child:
				child_doc=frappe.get_doc('Member',item.name)
				child_doc.active=0
				if child_doc.membership_expiry_date:
					if child_doc.membership_expiry_date>getdate(nowdate()):
						child_doc.membership_expiry_date=getdate(nowdate())
				child_doc.primary_member_id=''
				child_doc.self_relation=''
				child_doc.save()

@frappe.whitelist(allow_guest=True)
def check_subscription(self):
	if self.recurring_payment=="0":
		subscription=frappe.db.get_all('Braintree Subscriptions',fields=['*'],
			filters={'parent':self.email,'subscription_for':'Membership','status':'Active'},order_by='creation desc')
		if subscription:
			from gscommunity.templates.pages.braintreepayment import cancel_subscription
			result=cancel_subscription(subscription[0].subscription_id)
			if result.is_success:
				frappe.db.set_value('Braintree Subscriptions',subscription[0].name,'status','Cancelled')
	elif self.recurring_payment=="1":
		subscription=frappe.db.get_all('Braintree Subscriptions',fields=['*'],
			filters={'parent':self.email,'subscription_for':'Membership','status':'Active'},order_by='creation desc')
		if subscription:
			if float(self.membership_amount)!=float(subscription[0].amount):
				from gscommunity.templates.pages.braintreepayment import update_subscriptions
				plan=frappe.db.get_all('Braintree Plans',filters={'price':self.membership_amount},fields=['*'])
				if plan:
					result=update_subscriptions(subscription[0].subscription_id,plan[0].name,plan[0].price)

@frappe.whitelist()
def get_member_exipry_date(member_id):
	mem_end_date = frappe.db.get_all("Membership",
				filters={"member":member_id},order_by='creation desc',
				fields=['to_date'],limit_page_length=1)
	if mem_end_date:
		return mem_end_date[0]

					