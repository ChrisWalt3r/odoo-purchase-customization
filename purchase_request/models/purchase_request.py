# -*- coding: utf-8 -*-
# Part of Purchase Request module.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseRequest(models.Model):
    _name = 'purchase.request'
    _description = 'Purchase Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Request Reference',
        required=True,
        default='New',
        readonly=True,
        copy=False,
        index=True,
    )
    description = fields.Text(
        string='Purpose / Justification',
        help='Explain why this purchase is needed.',
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Requested By',
        required=True,
        default=lambda self: self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1
        ),
        tracking=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        related='employee_id.department_id',
        store=True,
        readonly=True,
    )
    manager_id = fields.Many2one(
        'hr.employee',
        string='Department Manager',
        related='employee_id.parent_id',
        store=True,
        readonly=True,
    )

    request_date = fields.Date(
        string='Request Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    date_required = fields.Date(
        string='Date Required',
        help='Date by which the items are needed.',
        tracking=True,
    )

    line_ids = fields.One2many(
        'purchase.request.line',
        'request_id',
        string='Request Lines',
        copy=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rfq_created', 'RFQ Created'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, index=True)

    rfq_id = fields.Many2one(
        'purchase.order',
        string='Generated RFQ',
        readonly=True,
        copy=False,
    )
    rfq_count = fields.Integer(
        compute='_compute_rfq_count',
        string='RFQ Count',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        string='Currency',
        readonly=True,
    )

    estimated_total = fields.Monetary(
        compute='_compute_estimated_total',
        string='Estimated Total',
        store=True,
        currency_field='currency_id',
    )

    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string='Approved Date',
        readonly=True,
        copy=False,
    )

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
    ], string='Priority', default='0', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'purchase.request'
                ) or 'New'
        return super().create(vals_list)

    @api.depends('line_ids.estimated_cost')
    def _compute_estimated_total(self):
        for request in self:
            request.estimated_total = sum(
                request.line_ids.mapped('estimated_cost')
            )

    @api.depends('rfq_id')
    def _compute_rfq_count(self):
        for request in self:
            request.rfq_count = 1 if request.rfq_id else 0

    # -------------------------------------------------------------------------
    # State Transition Actions
    # -------------------------------------------------------------------------
    def action_submit(self):
        """Submit the request for approval."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Cannot submit a request without any lines.'))
        self.write({'state': 'submitted'})

        # Notify the department manager if exists
        if self.manager_id and self.manager_id.user_id:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.manager_id.user_id.id,
                summary=_('Purchase Request "%s" needs approval') % self.name,
                note=_(
                    'Employee %s has submitted a purchase request that needs your review.'
                ) % self.employee_id.name,
            )

    def action_approve(self):
        """Approve the purchase request."""
        self.ensure_one()
        self.write({
            'state': 'approved',
            'approved_by': self.env.uid,
            'approved_date': fields.Datetime.now(),
        })

        # Post a chatter message
        self.message_post(
            body=_('Purchase request approved by %s.') % self.env.user.name,
            message_type='notification',
        )

    def action_reject(self):
        """Reject the purchase request."""
        self.ensure_one()
        self.write({'state': 'rejected'})
        self.message_post(
            body=_('Purchase request rejected by %s.') % self.env.user.name,
            message_type='notification',
        )

    def action_cancel(self):
        """Cancel the purchase request."""
        self.ensure_one()
        if self.state == 'rfq_created' and self.rfq_id:
            raise UserError(
                _('Cannot cancel a request that already has an RFQ. Cancel the RFQ first.')
            )
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        """Reset to draft state."""
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_create_rfq(self):
        """Create an RFQ from the approved purchase request."""
        self.ensure_one()
        if self.state != 'approved':
            raise UserError(_('Can only create RFQ from an approved request.'))
        if not self.line_ids:
            raise UserError(_('Cannot create an RFQ without request lines.'))

        # Create a new draft RFQ (partner_id will be set later via multi-vendor)
        # Use a dummy or first available vendor as placeholder since partner_id is required
        # The actual vendors will be added via the RFQ Vendors tab
        rfq_vals = {
            'origin': self.name,
            'date_order': fields.Datetime.now(),
            'company_id': self.company_id.id,
            'user_id': self.env.uid,
            'notes': _('Generated from Purchase Request: %s\nPurpose: %s') % (
                self.name, self.description or ''
            ),
        }

        # We need a partner_id since it's required on purchase.order
        # The procurement officer should set the proper vendor(s) via the multi-vendor tab
        # Use a placeholder approach: set partner_id to company's partner
        rfq_vals['partner_id'] = self.company_id.partner_id.id

        rfq = self.env['purchase.order'].create(rfq_vals)

        # Create RFQ lines from request lines
        for line in self.line_ids:
            po_line_vals = {
                'order_id': rfq.id,
                'product_id': line.product_id.id,
                'name': line.description or line.product_id.display_name,
                'product_qty': line.quantity,
                'product_uom': line.product_uom_id.id,
                'price_unit': line.estimated_unit_price,
                'date_planned': self.date_required or fields.Datetime.now(),
            }
            self.env['purchase.order.line'].create(po_line_vals)

        # Link the RFQ back to this request
        rfq.write({'purchase_request_id': self.id})

        # Update request state
        self.write({
            'state': 'rfq_created',
            'rfq_id': rfq.id,
        })

        # Post message on both records
        self.message_post(
            body=_(
                'RFQ <a href="/odoo/purchase/%s">%s</a> has been created from this request.'
            ) % (rfq.id, rfq.name),
            message_type='notification',
        )
        rfq.message_post(
            body=_(
                'Created from Purchase Request <b>%s</b> by %s (%s).'
            ) % (self.name, self.employee_id.name, self.department_id.name or ''),
            message_type='notification',
        )

        return {
            'name': _('Request for Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': rfq.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_rfq(self):
        """View the generated RFQ."""
        self.ensure_one()
        if not self.rfq_id:
            raise UserError(_('No RFQ has been generated for this request.'))
        return {
            'name': _('RFQ'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.rfq_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class PurchaseRequestLine(models.Model):
    _name = 'purchase.request.line'
    _description = 'Purchase Request Line'
    _order = 'request_id, sequence, id'

    request_id = fields.Many2one(
        'purchase.request',
        string='Purchase Request',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('purchase_ok', '=', True)]",
    )
    description = fields.Text(
        string='Description',
        compute='_compute_description',
        store=True,
        readonly=False,
    )
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure',
    )
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
        compute='_compute_product_uom_id',
        store=True,
        readonly=False,
    )
    product_uom_category_id = fields.Many2one(
        related='product_id.uom_id.category_id',
    )
    estimated_unit_price = fields.Float(
        string='Est. Unit Price',
        digits='Product Price',
        help='Estimated unit price for budgeting purposes.',
    )
    estimated_cost = fields.Monetary(
        compute='_compute_estimated_cost',
        string='Est. Total',
        store=True,
        currency_field='currency_id',
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='request_id.currency_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        related='request_id.company_id',
        store=True,
        readonly=True,
    )

    specifications = fields.Text(
        string='Specifications',
        help='Technical specifications or special requirements.',
    )

    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            if line.product_id:
                line.description = line.product_id.display_name
            else:
                line.description = ''

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_po_id or line.product_id.uom_id
            if not line.product_uom_id:
                line.product_uom_id = self.env.ref('uom.product_uom_unit', raise_if_not_found=False)

    @api.depends('quantity', 'estimated_unit_price')
    def _compute_estimated_cost(self):
        for line in self:
            line.estimated_cost = line.quantity * line.estimated_unit_price

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.estimated_unit_price = self.product_id.standard_price
