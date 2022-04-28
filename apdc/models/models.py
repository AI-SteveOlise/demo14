# -*- coding: utf-8 -*-

import base64
from odoo import api, fields, models, _
import datetime
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from ast import literal_eval
from odoo import tools
from odoo.modules.module import get_module_resource
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = 'sale.order'
    
    discount_request = fields.Boolean(string='Discount Request', copy=False)
    
    
    #@api.multi
    def create_discount_request(self):
        """
        Method to open create atp form
        """
        
        #partner_id = self.client_id
        #client_id = self.client_id
        #store_request_id = self.id
        #sub_account_id = self.sub_account_id
        #product_id = self.move_lines.product_id
             
        view_ref = self.env['ir.model.data'].get_object_reference('apdc', 'apdc_discount_request_form_view')
        view_id = view_ref[1] if view_ref else False
        
        #purchase_line_obj = self.env['purchase.order.line']
        for subscription in self:
            order_lines = []
            for line in subscription.order_line:
                order_lines.append((0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'qty': line.product_uom_qty,
                    #'date_planned': date.today(),
                    'unit_price': line.price_unit,
                }))
         
        res = {
            'type': 'ir.actions.act_window',
            'name': ('Discount Request'),
            'res_model': 'discount.request',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': {'default_partner_id': self.partner_id.id, 'default_sale_order_id': self.id, 'default_source': self.name, 'default_discount_request_line_ids': order_lines}
        }
        
        return res

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    
    discount = fields.Float(string='Discount', readonly=True)
    
    house_type = fields.Selection([
        ('nhf_fi=', 'NHF Fully Built'),
        ('nhf_carcass', 'NHF CARCASS'),
        ('none_nhf_fi=', 'None NHF Fully Built'),
        ('none_fully_nhf_carcass', 'None NHF CARCASS'),
        ], string='House Type', readonly=False, index=True, copy=False, track_visibility='onchange')
    
    house_category = fields.Selection([
        ('1bd=', '1 Bedroom'),
        ('2bd=', '2 Bedroom'),
        ('3bd=', '3 Bedroom'),
        ('4bd=', '4 Bedroom'),
        ], string='House Category', readonly=False, index=True, copy=False, track_visibility='onchange')
    
    
class DiscountRequest(models.Model):
    _name = 'discount.request'
    _description = 'Discount Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date DESC'
    
    state = fields.Selection([
        ('draft', 'New'),
        ('submit', 'Submitted'),
        ('approve', 'Approved'),
        ('reject', 'Reject'),
        ], string='Status', readonly=False, index=True, copy=False, default='draft', track_visibility='onchange')
    
    discount_request_line_ids = fields.One2many('discount.request.lines', 'discount_request_id', string="discount request Lines", copy=True)
    
    name = fields.Char('Order Reference', readonly=True, required=True, index=True, copy=False, default='New')
    date = fields.Date(string='Date', required=True, track_visibility='onchange', default=date.today())
    partner_id = fields.Many2one(comodel_name='res.partner', string='Client', required=True, track_visibility='onchange')
    sale_order_id = fields.Many2one(comodel_name='sale.order', string='Sale Order', track_visibility='onchange')
    remark = fields.Char(string='Remark', required=False)
    
    total = fields.Float(string='Total', compute='_total_unit', readonly=True)
    
    source = fields.Char(string='Source', copy=False)
    
    total_discount_approved = fields.Float(string='Total Discount Approved', compute='_total_discount_approved', readonly=True)
    
    #@api.one
    @api.depends('discount_request_line_ids.unit_price')
    def _total_unit(self):
        self.ensure_one()
        for line in self.discount_request_line_ids:
            self.total += line.price_subtotal
    
    #@api.one
    @api.depends('discount_request_line_ids.discount_approved')
    def _total_discount_approved(self):
        self.ensure_one()
        for line in self.discount_request_line_ids:
            self.total_discount_approved += line.discount_approved
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('discount.request') or '/'
        return super(DiscountRequest, self).create(vals)
    
    #@api.multi
    def button_submit(self):
        self.write({'state':'submit'})
        group_id = self.env['ir.model.data'].xmlid_to_object('apdc.group_md')
        user_ids = []
        partner_ids = []
        for user in group_id.users:
            user_ids.append(user.id)
            partner_ids.append(user.partner_id.id)
        self.message_subscribe(partner_ids=partner_ids)
        subject = "Discount Request '{}' needs approval".format(self.name)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
        return False
        
    #@api.multi
    def button_approval(self):
        self.write({'state':'approve'})
        if self.total_discount_approved == 0.00:
            for line in self.discount_request_line_ids:
                line.discount_approved = line.discount_request
        for sale in self.sale_order_id.order_line:
            for discount in self.discount_request_line_ids:
                sale.discount = discount.discount_approved
        #group_id = self.env['ir.model.data'].xmlid_to_object('purchase.group_purchase_manager')
        #user_ids = []'
        subject = "Discount Request '{}' has been approved".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
    #@api.multi
    def button_reject(self):
        self.write({'state':'reject'})
        subject = "Discount Request '{}' has been Rejected".format(self.name)
        partner_ids = []
        for partner in self.message_partner_ids:
            partner_ids.append(partner.id)
        self.message_post(subject=subject,body=subject,partner_ids=partner_ids)
    
class DiscountRequestLines(models.Model):
    _name = 'discount.request.lines'
    
    discount_request_id = fields.Many2one(comodel_name='discount.request', string='discount request')
    
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    name = fields.Char(string='Description', required=True)
    qty = fields.Float(string='Quantity', required=True)
    unit_price = fields.Float(string='Unit Price', required=False)
    discount_request = fields.Float(string='Discount Requested (%)', required=False)
    discount_approved = fields.Float(string='Discount Approved (%)', required=False)
    
    @api.onchange('product_id')
    def _onchange_partner_id(self):
        self.name = self.product_id.name
        self.unit_price = self.product_id.standard_price
    
    #@api.one
    def _check_user_group(self):
        for user in self:
            if user.user_has_groups('apdc.group_md'):
                user.is_manager = True
    
    is_manager = fields.Boolean(compute='_check_user_group')
    
    price_subtotal = fields.Float(string='Price Subtotal', readonly=True, compute='_price_subtotal')
    
    #@api.one
    def _price_subtotal(self):
        price = 0
        for line in self:
            price = line.unit_price * line.qty
            line.price_subtotal = price * (1 - (line.discount_approved or 0.0) / 100.0)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    house_type = fields.Selection([
        ('nhf_fi=', 'Fully Built'),
        ('nhf_carcass', 'CARCASS'),
        ('none_nhf_fi=', 'Substructure blocks'),
        ('none_fully_nhf_carcass', 'Commercial properties'),
        ], string='House Type', readonly=False, index=True, copy=False, track_visibility='onchange')
    
class Lead(models.Model):
    _inherit = 'crm.lead'    
    
    @api.model
    def _default_image(self):
        image_path = get_module_resource('hr', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))
    
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        "Photo", attachment=True,
        help="This field holds the image used as photo for the applicant, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized photo", attachment=True,
        help="Medium-sized photo of the employee. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized photo", attachment=True,
        help="Small-sized photo of the employee. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    

class SaleReport(models.Model):
    _inherit = 'sale.report'
    
    house_type = fields.Selection([
        ('nhf_fi=', 'NHF Fully Built'),
        ('nhf_carcass', 'NHF CARCASS'),
        ('none_nhf_fi=', 'None NHF Fully Built'),
        ('none_fully_nhf_carcass', 'None NHF CARCASS'),
        ], string='House Type', readonly=False, index=True, copy=False, track_visibility='onchange')
    
    house_category = fields.Selection([
        ('1bd=', '1 Bedroom'),
        ('2bd=', '2 Bedroom'),
        ('3bd=', '3 Bedroom'),
        ('4bd=', '4 Bedroom'),
        ], string='House Category', readonly=False, index=True, copy=False, track_visibility='onchange')
    
    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['house_type'] = ', l.house_type as house_type'
        fields['house_category'] = ', l.house_category as house_category'

        groupby += ', l.house_type, l.house_category'

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)


class AccountMove(models.Model):
    _inherit = "account.move"
    
    amount_paid = fields.Float(string='Total Amount Paid', compute='_amount_paid', readonly=True)
    
    percentage_amount_paid = fields.Float(string='Percentage of Total Amount Paid', compute='_percentage_amount_paid', readonly=True)
    
    #@api.depends('amount_total', 'amount_residual')
    def _amount_paid(self):
        #self.ensure_one()
        for amount in self:
            amount.amount_paid = amount.amount_total - amount.amount_residual
            
    #@api.depends('amount_total', 'amount_paid')
    def _percentage_amount_paid(self):
        #self.ensure_one()
        for amount in self:
            amount.percentage_amount_paid = amount.amount_paid / amount.amount_total * 100

class AccountAccount(models.Model):
    _inherit = "account.account"

    active = fields.Boolean(string='Active', default=True)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    amount_to_text = fields.Char(compute='_compute_amount_to_text')

    def _compute_amount_to_text(self):
        for rec in self:
            rec.amount_to_text = rec.currency_id.amount_to_text(rec.amount)
