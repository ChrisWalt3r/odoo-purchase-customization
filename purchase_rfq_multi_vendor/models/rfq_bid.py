# -*- coding: utf-8 -*-
# Part of Purchase Multi-Vendor RFQ module.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RFQBid(models.Model):
    _name = 'purchase.rfq.bid'
    _description = 'RFQ Vendor Bid'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'amount_total asc, id desc'

    name = fields.Char(
        string='Bid Reference',
        required=True,
        default='New',
        readonly=True,
        copy=False,
    )

    rfq_vendor_id = fields.Many2one(
        'purchase.rfq.vendor',
        string='RFQ Vendor',
        required=True,
        ondelete='cascade',
        index=True,
    )
    rfq_id = fields.Many2one(
        'purchase.order',
        related='rfq_vendor_id.rfq_id',
        string='RFQ Reference',
        store=True,
        readonly=True,
        index=True,
    )
    vendor_id = fields.Many2one(
        'res.partner',
        related='rfq_vendor_id.vendor_id',
        string='Vendor',
        store=True,
        readonly=True,
    )

    bid_date = fields.Datetime(
        string='Bid Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True,
    )
    validity_date = fields.Date(
        string='Bid Valid Until',
        help='Date until which this bid is valid.',
    )

    bid_line_ids = fields.One2many(
        'purchase.rfq.bid.line',
        'bid_id',
        string='Bid Lines',
        copy=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('awarded', 'Awarded'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    currency_id = fields.Many2one(
        'res.currency',
        related='rfq_id.currency_id',
        string='Currency',
        readonly=True,
        store=True,
    )

    amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    amount_tax = fields.Monetary(
        string='Taxes',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )
    amount_total = fields.Monetary(
        string='Total Amount',
        compute='_compute_amount',
        store=True,
        currency_field='currency_id',
    )

    delivery_terms = fields.Text(string='Delivery Terms')
    payment_terms = fields.Text(string='Payment Terms')
    notes = fields.Html(string='Vendor Notes')

    company_id = fields.Many2one(
        'res.company',
        related='rfq_id.company_id',
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'purchase.rfq.bid'
                ) or 'New'
        return super().create(vals_list)

    @api.depends('bid_line_ids.price_subtotal', 'bid_line_ids.price_tax')
    def _compute_amount(self):
        for bid in self:
            amount_untaxed = sum(bid.bid_line_ids.mapped('price_subtotal'))
            amount_tax = sum(bid.bid_line_ids.mapped('price_tax'))
            bid.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def action_submit(self):
        """Submit the bid for review."""
        self.ensure_one()
        if not self.bid_line_ids:
            raise UserError(_('Cannot submit a bid without any bid lines.'))
        if any(line.price_unit <= 0 for line in self.bid_line_ids):
            raise UserError(_('All bid lines must have a unit price greater than zero.'))

        self.write({'state': 'submitted'})
        # Update vendor link status
        self.rfq_vendor_id.write({
            'status': 'bid_received',
            'response_date': fields.Datetime.now(),
        })

    def action_under_review(self):
        """Mark bid as under review."""
        self.ensure_one()
        self.write({'state': 'under_review'})

    def action_award(self):
        """Open the award wizard to confirm and create PO."""
        self.ensure_one()
        if self.state not in ('submitted', 'under_review'):
            raise UserError(_('Only submitted or under-review bids can be awarded.'))

        return {
            'name': _('Award Bid & Create Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.rfq.select.winner.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_bid_id': self.id,
                'default_rfq_id': self.rfq_id.id,
            },
        }

    def action_reject(self):
        """Reject this bid."""
        self.ensure_one()
        self.write({'state': 'rejected'})
        # If no other bids are submitted/awarded, update vendor status
        other_active_bids = self.rfq_vendor_id.bid_ids.filtered(
            lambda b: b.id != self.id and b.state in ('submitted', 'under_review', 'awarded')
        )
        if not other_active_bids:
            self.rfq_vendor_id.write({'status': 'rejected'})

    def action_reset_draft(self):
        """Reset bid to draft state."""
        self.ensure_one()
        self.write({'state': 'draft'})


class RFQBidLine(models.Model):
    _name = 'purchase.rfq.bid.line'
    _description = 'RFQ Bid Line'
    _order = 'bid_id, sequence, id'

    bid_id = fields.Many2one(
        'purchase.rfq.bid',
        string='Bid',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    rfq_line_id = fields.Many2one(
        'purchase.order.line',
        string='RFQ Line',
        required=True,
        help='The original RFQ line this bid line corresponds to.',
    )

    product_id = fields.Many2one(
        'product.product',
        related='rfq_line_id.product_id',
        string='Product',
        readonly=True,
        store=True,
    )
    product_description = fields.Text(
        related='rfq_line_id.name',
        string='Description',
        readonly=True,
    )
    product_qty = fields.Float(
        related='rfq_line_id.product_qty',
        string='Requested Qty',
        readonly=True,
        store=True,
    )
    product_uom = fields.Many2one(
        'uom.uom',
        related='rfq_line_id.product_uom',
        string='Unit of Measure',
        readonly=True,
        store=True,
    )

    # Vendor bid values
    price_unit = fields.Float(
        string='Unit Price (Bid)',
        required=True,
        digits='Product Price',
        help='Unit price offered by the vendor.',
    )
    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
    )
    taxes_id = fields.Many2many(
        'account.tax',
        string='Taxes',
        domain=[('type_tax_use', '=', 'purchase')],
    )
    delivery_lead_time = fields.Integer(
        string='Lead Time (Days)',
        help='Number of days for delivery after order confirmation.',
    )

    price_subtotal = fields.Monetary(
        compute='_compute_amount',
        string='Subtotal',
        store=True,
    )
    price_tax = fields.Float(
        compute='_compute_amount',
        string='Tax Amount',
        store=True,
    )
    price_total = fields.Monetary(
        compute='_compute_amount',
        string='Total',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='bid_id.currency_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='bid_id.company_id',
        store=True,
        readonly=True,
    )

    @api.depends('product_qty', 'price_unit', 'discount', 'taxes_id')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.taxes_id.compute_all(
                price,
                line.currency_id,
                line.product_qty,
                product=line.product_id,
                partner=line.bid_id.vendor_id if line.bid_id else False,
            )
            line.update({
                'price_tax': sum(
                    t.get('amount', 0.0) for t in taxes.get('taxes', [])
                ),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
