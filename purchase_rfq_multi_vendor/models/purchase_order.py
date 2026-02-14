# -*- coding: utf-8 -*-
# Part of Purchase Multi-Vendor RFQ module.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # -------------------------------------------------------------------------
    # Multi-Vendor RFQ Fields
    # -------------------------------------------------------------------------
    rfq_vendor_ids = fields.One2many(
        'purchase.rfq.vendor',
        'rfq_id',
        string='RFQ Vendors',
        help='Vendors assigned to this RFQ.',
    )
    rfq_bid_ids = fields.One2many(
        'purchase.rfq.bid',
        'rfq_id',
        string='Received Bids',
        help='Bids received from vendors for this RFQ.',
    )

    vendor_count = fields.Integer(
        compute='_compute_vendor_count',
        string='Vendor Count',
    )
    bid_count = fields.Integer(
        compute='_compute_bid_count',
        string='Bid Count',
    )
    awarded_bid_id = fields.Many2one(
        'purchase.rfq.bid',
        string='Awarded Bid',
        readonly=True,
        copy=False,
        help='The bid that was awarded for this RFQ.',
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------
    @api.depends('rfq_vendor_ids')
    def _compute_vendor_count(self):
        for order in self:
            order.vendor_count = len(order.rfq_vendor_ids)

    @api.depends('rfq_bid_ids')
    def _compute_bid_count(self):
        for order in self:
            order.bid_count = len(order.rfq_bid_ids)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_send_to_all_vendors(self):
        """Send RFQ to all assigned vendors that haven't been sent yet."""
        self.ensure_one()
        if not self.rfq_vendor_ids:
            raise UserError(
                _('Please add at least one vendor to the RFQ before sending.')
            )

        vendors_to_send = self.rfq_vendor_ids.filtered(
            lambda v: v.status == 'draft'
        )
        if not vendors_to_send:
            raise UserError(
                _('All vendors have already been sent the RFQ.')
            )

        # Separate vendors with and without email
        vendors_with_email = vendors_to_send.filtered(
            lambda v: v.vendor_id.email
        )
        vendors_no_email = vendors_to_send - vendors_with_email

        # Mark all vendors as sent (even those without email for testing)
        vendors_to_send.write({
            'status': 'sent',
            'sent_date': fields.Datetime.now(),
        })

        # Build notification message
        warning_msg = ''
        if vendors_no_email:
            names = ', '.join(vendors_no_email.mapped('vendor_id.name'))
            warning_msg = _(' (Note: %s have no email - marked as sent but no email dispatched)') % names

        # Update RFQ state to sent
        if self.state == 'draft':
            self.write({'state': 'sent'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': _('RFQ sent to %d vendor(s).%s') % (len(vendors_to_send), warning_msg),
                'type': 'success' if not vendors_no_email else 'warning',
                'sticky': False,
            },
        }

    def action_view_rfq_vendors(self):
        """View all vendors assigned to this RFQ."""
        self.ensure_one()
        return {
            'name': _('RFQ Vendors'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq.vendor',
            'view_mode': 'list,form',
            'domain': [('rfq_id', '=', self.id)],
            'context': {'default_rfq_id': self.id},
        }

    def action_view_rfq_bids(self):
        """View all bids for this RFQ."""
        self.ensure_one()
        return {
            'name': _('Bids for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq.bid',
            'view_mode': 'list,form',
            'domain': [('rfq_id', '=', self.id)],
            'context': {
                'default_rfq_id': self.id,
                'search_default_rfq_id': self.id,
            },
        }

    def action_compare_bids(self):
        """Open a comparison view of all submitted bids."""
        self.ensure_one()
        submitted_bids = self.rfq_bid_ids.filtered(
            lambda b: b.state in ('submitted', 'under_review')
        )
        if not submitted_bids:
            raise UserError(
                _('No submitted bids to compare. Please ensure vendors have submitted their bids.')
            )

        return {
            'name': _('Compare Bids for %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq.bid',
            'view_mode': 'list,form',
            'domain': [('id', 'in', submitted_bids.ids)],
            'context': {'default_rfq_id': self.id},
        }
