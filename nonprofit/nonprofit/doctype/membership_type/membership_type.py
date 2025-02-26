# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
from frappe.model.document import Document

class MembershipType(Document):
	def validate(self):
		self.calculate_total()
		
	def calculate_total(self):
		"""Calculates total amount."""
		self.count = 0
		for d in self.tab_11:
			self.count += d.allowed_members
