from __future__ import unicode_literals
from frappe.model.document import Document
from frappe import _
import json
import frappe
from six import string_types
from frappe.model.utils import get_fetch_values
from frappe.model.mapper import get_mapped_doc
from erpnext.stock.stock_balance import update_bin_qty, get_reserved_qty
from frappe.desk.notifications import clear_doctype_notifications
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.controllers.selling_controller import SellingController
from frappe.desk.doctype.auto_repeat.auto_repeat import get_next_schedule_date
from erpnext.selling.doctype.customer.customer import check_credit_limit
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults
from erpnext.manufacturing.doctype.production_plan.production_plan import get_items_for_material_requests
from frappe.utils import cstr, flt, getdate, comma_and, cint, nowdate, add_days

@frappe.whitelist()
def get_customer_for_visit(customer):
	hasil = frappe.db.sql(""" SELECT 
		cust.name, cust.`territory`, cust.`customer_group`, 
		tc.`mobile_no`,
		ta.`address_line1`, ta.`address_line2`
		FROM 
		`tabCustomer` cust
		LEFT JOIN
		`tabDynamic Link` dl ON dl.`link_name` = cust.name and dl.`parenttype` = "Address"
		LEFT JOIN `tabAddress` ta ON ta.name = dl.parent
		LEFT JOIN
		`tabDynamic Link` dl2 ON dl2.`link_name` = cust.name AND dl2.`parenttype` = "Contact"
		LEFT JOIN `tabContact` tc ON tc.name = dl2.parent
		WHERE
		dl.link_doctype = "Customer"
		AND 
		(dl.parenttype = "Address"
		OR 
		dl.parenttype = "Contact")
		AND cust.name LIKE "%{}%"
	""".format(customer), as_dict=1)
	return hasil

@frappe.whitelist()
def search_customer_for_visit(customer):
	hasil = frappe.db.sql(""" SELECT 
		cust.name, cust.`territory`, cust.`customer_group`, 
		tc.`mobile_no`,
		ta.`address_line1`, ta.`address_line2`
		FROM 
		`tabCustomer` cust
		LEFT JOIN
		`tabDynamic Link` dl ON dl.`link_name` = cust.name and dl.`parenttype` = "Address"
		LEFT JOIN `tabAddress` ta ON ta.name = dl.parent
		LEFT JOIN
		`tabDynamic Link` dl2 ON dl2.`link_name` = cust.name AND dl2.`parenttype` = "Contact"
		LEFT JOIN `tabContact` tc ON tc.name = dl2.parent
		WHERE
		dl.link_doctype = "Customer"
		AND 
		(dl.parenttype = "Address"
		OR 
		dl.parenttype = "Contact")
		AND cust.name = "{}"
	""".format(customer), as_dict=1)
	return hasil

@frappe.whitelist()
def get_company():
	hasil = frappe.db.sql(""" SELECT 
		name FROM `tabCompany`
	""", as_dict=1)
	return hasil

@frappe.whitelist()
def post_customer_address_contact(data):
	try:
		hasil_json = json.loads(str(data))
	except:
		return "JSON fails to decode."

	hasil_keys = hasil_json.keys()

	keys_to_check = [
		"customer_name",
		"customer_group",
		"sales",
		"credit_limit",
		"payment_terms",
		"industry",
		"market_segment",
		"company",
		"address_type",
		"address_line1",
		"city",
		"state",
		"country",
		"first_name",
		"email_id",
		"gender",
		"contact_phone",
		"contact_mobile_no",
		"designation"

	]

	for row in keys_to_check:
		if row not in hasil_keys:
			return "Fail to find {} attribute from data sent.".format(row)

	check_customer = frappe.db.sql(""" SELECT name FROM `tabCustomer` WHERE customer_name = "{}" """.format(hasil_json["customer_name"]))
	if len(check_customer) > 0:
		return "Customer {} already exists. Please use another name.".format(hasil_json["customer_name"])

	customer = frappe.new_doc("Customer")
	customer.customer_name = hasil_json["customer_name"]
	customer.customer_group = hasil_json["customer_group"]
	customer.territory = hasil_json["territory"]
	customer.sales = hasil_json["sales"]
	customer.credit_limit = hasil_json["credit_limit"]
	customer.payment_terms = hasil_json["payment_terms"]
	customer.industry = hasil_json["industry"]
	customer.market_segment = hasil_json["market_segment"]
	customer.company = hasil_json["company"]
	customer.recommended_by = hasil_json["recommended_by"]

	if "tax_id" in str(hasil_json):
		customer.tax_id = hasil_json["tax_id"]
	if "customer_details" in str(hasil_json):
		customer.customer_details = hasil_json["customer_details"]

	customer.save()

	hasil_customer = customer.name

	address_title = hasil_customer + "-Address"

	address = frappe.new_doc("Address")
	address.address_title = address_title

	address.partner_type = hasil_json["address_type"]
	address.address_line1 = hasil_json["address_line1"]
	address.is_primary_address = hasil_json["is_primary_address"]
	address.is_shipping_address = hasil_json["is_shipping_address"]
	address.city = hasil_json["city"]
	address.state = hasil_json["state"]
	address.country = hasil_json["country"]
	address.latitude = hasil_json["latitude"]
	address.longitude = hasil_json["longitude"]


	list_links = {
		"link_doctype" : "Customer",
        "link_name" : customer.name,
        "link_title" : customer.name
	}

	address.append("links", list_links)

	if "phone" in hasil_keys:
		address.phone = hasil_json["phone"]
	if "address_line2" in hasil_keys:
		address.address_line2 = hasil_json["address_line2"]
	if "pincode" in hasil_keys:
		address.pincode =  hasil_json["pincode"]

	address.save()

	
	contact = frappe.new_doc("Contact")

	contact.first_name = hasil_json["first_name"]
	contact.email_id = hasil_json["email_id"]
	contact.gender = hasil_json["gender"]
	contact.phone = hasil_json["contact_phone"]
	contact.mobile_no = hasil_json["contact_mobile_no"]
	contact.designation = hasil_json["designation"]

	if "last_name" in hasil_keys:
		contact.last_name = hasil_json["last_name"]
	if "department" in hasil_keys:	
		contact.department = hasil_json["department"]
	
	contact.append("links", list_links)

	contact.save()

	return {
		"status" : "Success",
		"customer": customer.name, 
		"address": address.name,
		"contact": contact.name
	}
