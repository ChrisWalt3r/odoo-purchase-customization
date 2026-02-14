# -*- coding: utf-8 -*-
{
    'name': 'Purchase Multi-Vendor RFQ',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Assign multiple vendors to RFQs, manage bids, and select winning bidders',
    'description': """
Purchase Multi-Vendor RFQ
=========================
This module extends the standard Purchase module to support:

- **Multi-Vendor RFQ**: Assign multiple vendors to a single Request for Quotation
- **Bid Management**: Receive and track bids from multiple vendors against an RFQ
- **Bid Comparison**: Compare bids side-by-side to evaluate vendor pricing
- **Winner Selection**: Select the winning bidder and automatically generate a Purchase Order

Workflow:
1. Create an RFQ and add product lines
2. Assign multiple vendors to the RFQ
3. Send the RFQ to all assigned vendors
4. Record bids received from each vendor
5. Compare bids and select the winning vendor
6. A Purchase Order is automatically created for the winning vendor
    """,
    'author': 'Custom Development',
    'depends': ['purchase', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'wizard/select_winner_wizard_views.xml',
        'views/rfq_vendor_views.xml',
        'views/rfq_bid_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
