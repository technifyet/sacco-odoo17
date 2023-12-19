from datetime import datetime
from odoo import models, fields


class SmifTransaction(models.Model):
    _name = 'smif.transaction'
    _rec_name = 'transaction_type'
    _description = 'Saving or Withdrawal Transaction'


    member_ids = fields.Many2one('smif.member',#,
                                 string='Member', index=True)
    account_ids = fields.Many2one('smif.member_account', string='Account', index=True)
    transaction_type = fields.Selection(
        string="Transaction Type", selection=[('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ],
        required=True, help="Select Transaction Type")
    transaction_balance = fields.Monetary(string="Transaction Balance", required=False, default=0 )
    transaction_amount = fields.Monetary(string="Amount", required=True, )
    transaction_date = fields.Datetime(string="Date Time", required=True,  default=datetime.now())
    # transaction_category = fields.Selection(string="Transaction Category",
    #                                         selection=[('compulsorySaving', 'Compulsory Saving'),
    #                                                    ('voluntarySaving', 'Voluntary Saving'),
    #                                                    ('fixedSaving', 'Fixed Saving')], required=True, )

    type_name = fields.Char(related='account_ids.type_name',)
    payment_method = fields.Selection(
        string="Payment Method", selection=[('cash', 'Cash'), ('bank', 'Bank'),('check', 'Check'),('transaction', 'Transaction') ],
        default='cash')
    bank_id = fields.Many2one('res.partner.bank', string="Bank Account")
    ref_number = fields.Char('Reference Number')
    check_number = fields.Char('Check Number')
    transaction_note = fields.Char('Note')

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    def get_display_color(self):
        if self.transaction_type =='deposit':
            return 'font-weight:bold; color:blue;'
        else:
            return 'font-weight:bold; color:red;'
