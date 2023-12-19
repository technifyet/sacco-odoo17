from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = ['res.config.settings']

    # Members Settings
    registration_fee = fields.Float(string="Registration Fee", config_parameter="smif.registration_fee", required=True,
                                    tracking=True, )

    maximum_share = fields.Integer(string="Shares Allowed", default=0, tracking=True,
                                   config_parameter="smif.shares_allowed",
                                   help='Maximum number of shares allowed for a member to purchase')
    calc_dividend_by = fields.Selection(string="Calculate Dividend By", config_parameter="smif.calc_dividend_by",
                                        selection=[('saving', 'Saving'), ('share', 'Share'),
                                                   ('both', 'Saving and Share')], required=False, )

    member_dividend_saving_percentage = fields.Float(string="Dividend Saving Percentage", tracking=True,
                                                     config_parameter="smif.member_dividend_saving_percentage", )
    member_dividend_share_percentage = fields.Float(string="Dividend SharePercentage", tracking=True,
                                                    config_parameter="smif.member_dividend_share_percentage", )

    member_dividend_percentage = fields.Float(string="Members Dividend Percentage", required=True, tracking=True,
                                              config_parameter="smif.member_dividend_percentage", )
    retained_earning = fields.Float(string="Retained Earning", required=True,
                                    tracking=True, config_parameter="smif.retained_earning", )
    membership_share_required = fields.Boolean(string="Membership Share Required", required=True,
                                               config_parameter="smif.membership_share_required", )
    auto_generate_member_id = fields.Boolean(string="Auto Generate Member ID", required=True,
                                             config_parameter="smif.auto_generate_member_id", )
    max_collateral_member_can_be = fields.Integer(string="Max Collateral Member Can Be", required=True,
                                                  config_parameter="smif.max_collateral_member_can_be", )

    # Saving Settings

    # compulsory_saving_amount = fields.Float(string="Compulsory Saving Amount", required=True, tracking=True, config_parameter="smif.compulsory_saving_amount",)
    minimum_saving_interest = fields.Float(string="Minimum Interest", required=True, tracking=True,
                                           config_parameter="smif.minimum_saving_interest", )
    maximum_saving_interest = fields.Float(string="Maximum Interest", required=True, tracking=True,
                                           config_parameter="smif.maximum_saving_interest", )

    # compulsory_saving_interest = fields.Float(string="Compulsory Saving Interest", required=True,
    #                                           tracking=True, config_parameter="smif.compulsory_saving_interest",)
    # voluntary_saving_interest = fields.Float(string="Voluntary Saving Interest", required=True,
    #                                          tracking=True, config_parameter="smif.voluntary_saving_interest",)
    # maximum_withdrawal_allowed = fields.Float(string="Allowed Maximum Withdrawal", required=True, tracking=True, config_parameter="smif.voluntary_saving_interest",)
    # compulsory_saving_withdrawal_allowed = fields.Boolean(string="Compulsory Saving Withdrawal Allowed", required=True,
    #                                                       tracking=True, config_parameter="smif.compulsory_saving_withdrawal_allowed",)
    # Loan Settings
    minimum_loan_interest = fields.Float(string="Minimum Interest", required=True, tracking=True,
                                         config_parameter="smif.minimum_loan_interest", )
    maximum_loan_interest = fields.Float(string="Maximum Interest", required=True, tracking=True,
                                         config_parameter="smif.maximum_loan_interest", )
    maximum_loan_allowed = fields.Float(string="Maximum Loan Allowed", required=True, tracking=True,
                                        config_parameter="smif.maximum_loan_allowed", )
    minimum_saving_months = fields.Integer(string="Minimum Saving Months", required=True, tracking=True,
                                           config_parameter="smif.minimum_saving_months", )
    maximum_loan_payment_period = fields.Integer(string="Maximum Payment Period", required=True, tracking=True,
                                                 config_parameter="smif.maximum_loan_payment_period", )
    loan_service_charge_in = fields.Selection(string="Service Charge",
                                              config_parameter="smif.loan_service_charge_in",
                                              selection=[('NA', 'No Service Charge'),
                                                         ('figure', 'Figure'),
                                                         ('percent', 'Percent')], required=True, )

    loan_service_charge = fields.Float(string="Loan Service Charge", required=True, tracking=True,
                                       config_parameter="smif.loan_service_charge", )
    loan_refinancing_in = fields.Selection(string="Service Charge",
                                           config_parameter="smif.loan_refinancing_in",
                                           selection=[('NA', 'No Refinancing'),
                                                      ('months', 'Number of Paid months'),
                                                      ('percent', 'Paid Percentage')], required=True, )
    minimum_loan_payment_for_refinance = fields.Float(string="Minimum Loan Payment for Refinance", required=True,
                                                      tracking=True,
                                                      config_parameter="smif.minimum_loan_payment_for_refinance", )
    loan_calculation_method = fields.Selection(string="Loan Calculation Method",
                                               config_parameter="smif.loan_calculation_method",
                                               selection=[('flat_balance', 'Flat Balance'),
                                                          ('amortization', 'Amortization'),
                                                          ('declining_balance', 'Declining Balance')], required=False, )
    saving_interest_period = fields.Selection(string="Calculate Interest Per",
                                              config_parameter="smif.saving_interest_period",
                                              selection=[('daily', 'Daily'),
                                                         ('monthly', 'Monthly'),
                                                         ('yearly', 'Yearly')], default='monthly', required=True, )

    minimum_deposit_duration_for_int = fields.Integer(string="Minimum Deposit Duration", required=True, tracking=True,
                                                 config_parameter="smif.minimum_deposit_duration_for_int", )

    # Chart of Account Config for Accounting

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 config_parameter="smif.company_id")
    saving_interest_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Default Saving Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.saving_interest_account")
    loan_interest_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Default Loan Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.loan_interest_account")
    penalty_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Default Penalty Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", config_parameter="smif.penalty_account")
    service_charge_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Default Service Charge Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.service_charge_account")
    reg_fee_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Default Registration Fee Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", config_parameter="smif.reg_fee_account")
    insurance_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Default Insurance Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.insurance_account")

    dvd_account_payable = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Dividend Account Payable', help='This is used for Account entry for total member dividend entry',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.dvd_account_payable")

    dvd_account_paid = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Dividend Account Paid', help='This is used for Account entry for each dividend amount',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.dvd_account_paid")

    retained_earning_account = fields.Many2one(
        'account.account', check_company=True, copy=False,
        string='Retained Earning Account', help='This is used for Account entry for company dividend amount',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
        config_parameter="smif.retained_earning_account")
