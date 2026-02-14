# -*- coding: utf-8 -*-
{
    'name': 'Purchase Request',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Employee purchase requests to the Procurement department',
    'description': """
Purchase Request
================
This module provides a workflow for employees to submit purchase requests
to the Procurement department.

Features:
- Employees create purchase requests for items they need
- Requests go through an approval workflow (Submit → Approve → Create RFQ)
- Procurement officers can review, approve, or reject requests
- Approved requests can be converted to multi-vendor RFQs
- Full audit trail with chatter integration

Workflow:
1. Employee creates a Purchase Request with required products
2. Employee submits the request for approval
3. Procurement Manager reviews and approves/rejects
4. Upon approval, a Procurement officer creates an RFQ from the request
5. The RFQ follows the standard multi-vendor bidding process
    """,
    'author': 'Custom Development',
    'depends': ['purchase_rfq_multi_vendor', 'hr'],
    'data': [
        'security/purchase_request_security.xml',
        'security/ir.model.access.csv',
        'data/sequence_data.xml',
        'views/purchase_request_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
