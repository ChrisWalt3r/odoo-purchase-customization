# -*- coding: utf-8 -*-
# Part of Purchase Multi-Vendor RFQ module.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SelectWinnerWizard(models.TransientModel):
    _name = 'purchase.rfq.select.winner.wizard'
    _description = 'Select Winning Bid Wizard'

    bid_id = fields.Many2one(
        'purchase.rfq.bid',
        string='Winning Bid',
        required=True,
    )
    rfq_id = fields.Many2one(
        'purchase.order',
        string='RFQ',
        required=True,
    )
    vendor_id = fields.Many2one(
        'res.partner',
        related='bid_id.vendor_id',
        string='Winning Vendor',
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='bid_id.currency_id',
        readonly=True,
    )
    amount_total = fields.Monetary(
        related='bid_id.amount_total',
        string='Bid Total Amount',
        currency_field='currency_id',
    )

    use_bid_pricing = fields.Boolean(
        string='Use Bid Pricing',
        default=True,
        help='If checked, the Purchase Order will use the prices from the winning bid. '
             'Otherwise, the original RFQ prices will be used.',
    )
    notes = fields.Text(
        string='Award Notes',
        help='Any additional notes about the award decision.',
    )

    def action_confirm_winner(self):
        """Award the selected bid and create a Purchase Order for the winning vendor."""
        self.ensure_one()

        if self.bid_id.state not in ('submitted', 'under_review'):
            raise UserError(
                _('Only submitted or under-review bids can be awarded.')
            )

        # 1. Mark winning bid as awarded
        self.bid_id.write({'state': 'awarded'})
        self.bid_id.rfq_vendor_id.write({'status': 'awarded'})

        # 2. Reject all other submitted bids for the same RFQ
        other_bids = self.rfq_id.rfq_bid_ids.filtered(
            lambda b: b.id != self.bid_id.id and b.state in ('submitted', 'under_review')
        )
        other_bids.write({'state': 'rejected'})
        for bid in other_bids:
            bid.rfq_vendor_id.write({'status': 'rejected'})

        # Reject vendors who haven't bid
        non_bidding_vendors = self.rfq_id.rfq_vendor_ids.filtered(
            lambda v: v.status not in ('awarded', 'rejected')
        )
        non_bidding_vendors.write({'status': 'rejected'})

        # 3. Create a new Purchase Order from the winning bid
        po_vals = {
            'partner_id': self.vendor_id.id,
            'origin': self.rfq_id.name,
            'date_order': fields.Datetime.now(),
            'company_id': self.rfq_id.company_id.id,
            'currency_id': self.rfq_id.currency_id.id,
            'fiscal_position_id': self.rfq_id.fiscal_position_id.id if self.rfq_id.fiscal_position_id else False,
            'payment_term_id': self.rfq_id.payment_term_id.id if self.rfq_id.payment_term_id else False,
            'notes': self.rfq_id.notes,
            'user_id': self.rfq_id.user_id.id if self.rfq_id.user_id else self.env.uid,
        }
        new_po = self.env['purchase.order'].create(po_vals)

        # 4. Copy lines from bid to PO
        for bid_line in self.bid_id.bid_line_ids:
            price = bid_line.price_unit if self.use_bid_pricing else bid_line.rfq_line_id.price_unit
            discount = bid_line.discount if self.use_bid_pricing else bid_line.rfq_line_id.discount

            line_vals = {
                'order_id': new_po.id,
                'product_id': bid_line.product_id.id,
                'name': bid_line.rfq_line_id.name or bid_line.product_id.display_name,
                'product_qty': bid_line.product_qty,
                'product_uom': bid_line.product_uom.id,
                'price_unit': price,
                'discount': discount,
                'date_planned': fields.Datetime.now(),
            }
            if bid_line.taxes_id:
                line_vals['taxes_id'] = [(6, 0, bid_line.taxes_id.ids)]
            elif bid_line.rfq_line_id.taxes_id:
                line_vals['taxes_id'] = [(6, 0, bid_line.rfq_line_id.taxes_id.ids)]

            self.env['purchase.order.line'].create(line_vals)

        # 5. Link awarded bid to RFQ
        self.rfq_id.write({
            'awarded_bid_id': self.bid_id.id,
        })

        # 6. Post a message on the RFQ chatter
        self.rfq_id.message_post(
            body=_(
                'Bid <b>%s</b> from vendor <b>%s</b> has been awarded. '
                'Purchase Order <a href="/odoo/purchase/%s">%s</a> has been created.'
            ) % (
                self.bid_id.name,
                self.vendor_id.name,
                new_po.id,
                new_po.name,
            ),
            message_type='notification',
        )

        # 7. Return the new PO form
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': new_po.id,
            'view_mode': 'form',
            'target': 'current',
        }
