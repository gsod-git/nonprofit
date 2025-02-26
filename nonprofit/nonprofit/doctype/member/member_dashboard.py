from frappe import _

def get_data():
	return {
		'heatmap': False,
		'heatmap_message': _('Member Activity'),
		'fieldname': 'member',
		'transactions': [
			{
				'label': _('Membership Details'),
				'items': ['Membership']
			},
			{
				'label': _('Donation'),
				'items': ['Donation']
			},
			{
				'label': _('Payment Details'),
				'items': ['Payment Entries']
			},
			{
				'label': _('Event Bookings'),
				'items': ['Bookings']
			}
		]
	}