# -*- coding: utf-8 -*-
# Part of Purchase Multi-Vendor RFQ module.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RFQVendor(models.Model):
    _name = 'purchase.rfq.vendor'
    _description = 'RFQ Vendor Assignment'
    _rec_name = 'vendor_id'
    _order = 'id desc'

    rfq_id = fields.Many2one(
        'purchase.order',
        string='RFQ',
        required=True,
        ondelete='cascade',
        index=True,
    )
    vendor_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        domain="[('supplier_rank', '>', 0)]",
        index=True,
    )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('bid_received', 'Bid Received'),
        ('awarded', 'Awarded'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft')

    sent_date = fields.Datetime(string='Sent Date', readonly=True)
    response_date = fields.Datetime(string='Response Date', readonly=True)
    notes = fields.Text(string='Notes')

    bid_ids = fields.One2many(
        'purchase.rfq.bid',
        'rfq_vendor_id',
        string='Bids',
    )
    bid_count = fields.Integer(
        compute='_compute_bid_count',
        string='Bid Count',
    )

    company_id = fields.Many2one(
        'res.company',
        related='rfq_id.company_id',
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='rfq_id.currency_id',
        store=True,
        readonly=True,
    )

    _sql_constraints = [
        ('unique_rfq_vendor',
         'UNIQUE(rfq_id, vendor_id)',
         'This vendor is already assigned to this RFQ!'),
    ]

    @api.depends('bid_ids')
    def _compute_bid_count(self):
        for record in self:
            record.bid_count = len(record.bid_ids)

    def action_send_rfq(self):
        """Mark this vendor line as RFQ Sent."""
        self.ensure_one()

        self.write({
            'status': 'sent',
            'sent_date': fields.Datetime.now(),
        })

        if not self.vendor_id.email:
            # No email - just mark as sent and notify
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': _('Vendor "%s" has no email. Marked as sent without email.') % self.vendor_id.name,
                    'type': 'warning',
                    'sticky': False,
                },
            }

        # Has email - open the email compose wizard
        template = self.env.ref(
            'purchase.email_template_edi_purchase', raise_if_not_found=False
        )

        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'purchase.order',
            'default_res_ids': self.rfq_id.ids,
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'default_partner_ids': [self.vendor_id.id],
            'force_email': True,
        })

        try:
            compose_form_id = self.env.ref('mail.email_compose_message_wizard_form').id
        except ValueError:
            compose_form_id = False

        return {
            'name': _('Send RFQ to %s') % self.vendor_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def action_mark_sent(self):
        """Quick mark as sent without email wizard."""
        self.ensure_one()
        self.write({
            'status': 'sent',
            'sent_date': fields.Datetime.now(),
        })

    def action_view_bids(self):
        """View bids from this vendor."""
        self.ensure_one()
        return {
            'name': _('Bids from %s') % self.vendor_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq.bid',
            'view_mode': 'list,form',
            'domain': [('rfq_vendor_id', '=', self.id)],
            'context': {
                'default_rfq_vendor_id': self.id,
                'default_rfq_id': self.rfq_id.id,
            },
        }

    def action_create_bid(self):
        """Create a new bid for this vendor."""
        self.ensure_one()
        bid = self.env['purchase.rfq.bid'].create({
            'rfq_vendor_id': self.id,
        })
        # Auto-populate bid lines from RFQ order lines
        for order_line in self.rfq_id.order_line.filtered(lambda l: not l.display_type):
            self.env['purchase.rfq.bid.line'].create({
                'bid_id': bid.id,
                'rfq_line_id': order_line.id,
                'price_unit': 0.0,
            })

        return {
            'name': _('New Bid from %s') % self.vendor_id.name,
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq.bid',
            'view_mode': 'form',
            'res_id': bid.id,
            'target': 'current',
        }
