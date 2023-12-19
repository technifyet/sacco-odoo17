from datetime import datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SmifShares(models.Model):
    _name = 'smif.shares'
    _rec_name = 'share_name'
    _description = 'Available Share to be sold to members'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    share_name = fields.Char(string="Share", required=True, tracking=True)
    totalInitialShareQuantity = fields.Integer(string="Total Share", required=True, tracking=True)
    remainingQuantity = fields.Integer(string="Remaining Quantity", required=False, tracking=False)
    unitPrice = fields.Monetary(string="Unit Price", required=True, tracking=True)
    share_creation_date = fields.Date(string="Date", required=True, default=datetime.today())

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Share Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", tracking=True, required=True)


    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    is_share_used=fields.Boolean(string='Share is being sold',default=False)

    @api.model
    def create(self, values):
        values.__setitem__('remainingQuantity',values['totalInitialShareQuantity'])
        return  super(SmifShares, self).create(values)

    def write(self, vals):
        if self.is_share_used:
            raise ValidationError("Share is already being sold. Cant be modified")
        else:
            if vals.__contains__('totalInitialShareQuantity'):
                vals.__setitem__('remainingQuantity',vals['totalInitialShareQuantity'])
            return super(SmifShares, self).write(vals)



    def save_shares_sales(self,sold_qnt):
        rmg_amount=self.remainingQuantity-sold_qnt
        assert rmg_amount>=0,'No Enough Share to Sale'
        vl={'remainingQuantity':rmg_amount,
            'is_share_used':True}
        super(SmifShares, self).write(vl)

class SmifMemberShare(models.Model):
    _name = 'smif.member_shares'
    # _rec_name = 'share.share_name'

    _description = 'Shares sold to member'

    member_id = fields.Many2one('smif.member',#,
                                string='Member', index=True)
    # share_name = fields.Char(string="Share", required=True, tracking=True)
    share = fields.Many2one('smif.shares', string='Share', )
    purchased_quantity = fields.Integer(string="Purchased Quantity", required=True, tracking=True)
    unit_price = fields.Monetary(string="Unit Price", related='share.unitPrice', readonly=True, tracking=False)
    purchased_date = fields.Date(string="Purchased Date", required=True, )
    total_amount = fields.Monetary(string='Total', store='False')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    is_accounting_set = fields.Boolean('Is Accounting Set', default=False)
    is_active = fields.Boolean('Is Active', default=True)
    @api.onchange('unit_price', 'purchased_quantity')
    def _compute_sum(self):
        self.total_amount = self.unit_price * self.purchased_quantity

    def save_member_share_sales(self,vals):
        # vals['total_amount']=vals['purchased_quantity']*self.unit_price
        res= super(SmifMemberShare, self).create(vals)

        return res

