# -*- coding: utf-8 -*-
# Part of Purchase Request module.

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        readonly=True,
        copy=False,
        help='The purchase request that originated this RFQ.',
    )
    purchase_request_count = fields.Integer(
        compute='_compute_purchase_request_count',
        string='Request Count',
    )

    @api.depends('purchase_request_id')
    def _compute_purchase_request_count(self):
        for order in self:
            order.purchase_request_count = 1 if order.purchase_request_id else 0

    def action_view_purchase_request(self):
        """View the originating purchase request."""
        self.ensure_one()
        if not self.purchase_request_id:
            return
        return {
            'name': _('Purchase Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.request',
            'res_id': self.purchase_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
