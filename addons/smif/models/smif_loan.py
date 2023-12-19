from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


def show_message(title, message_to_display, type):
    notification = {
        'type': "ir.actions.client",
        'tag': "display_notification",
        'params': {
            'title': title,
            'message': message_to_display,
            'type': type,
            'sticky': False,
        },
    }
    return notification


class SmifLoanType(models.Model):
    _name = 'smif.loan_type'
    _rec_name = 'loan_type'
    _description = 'Loan Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    loan_type = fields.Char(string="Loan Type", required=True, )
    interest_rate = fields.Float(string="Interest Rate", required=True, tracking=True, digits=(12, 2))
    payment_period = fields.Integer(string="Payment Period", default=0, tracking=True,
                                    help='Total number of months to finish payment')
    grace_period = fields.Integer(string="Grace Period",
                                  default=0, tracking=True,
                                  help='Maximum Number of months before starting payment.')

    loan_service_charge = fields.Selection(string="Loan Service Charge", tracking=True,
                                           selection=[('amount', 'Amount'), ('percentage', 'Percentage'),
                                                      ('NA', 'No Service Charge')], default='NA', required=True,
                                           help=" No Service Charge: There will be no service charge.\n"
                                                " Amount: Add fixed amount of loan service charge.\n"
                                                " Percentage: Calculate service charge based on set pecentage of loan amount.")

    service_charge = fields.Float(string="Service Charge", default=0,
                                  tracking=True,
                                  help="Loan Service Charge", digits=(12, 2))

    insurance_calculation = fields.Selection(string="Insurance", tracking=True,
                                             selection=[('amount', 'Amount'), ('percentage', 'Percentage'),
                                                        ('NA', 'No Insurance Charge')], default='percentage',
                                             required=True,
                                             help=" No Insurance Charge: There will be no Insurance charge.\n"
                                                  " Amount: Add fixed amount of loan service charge.\n"
                                                  " Percentage: Calculate Insurance based on set pecentage of loan amount.")

    insurance_amount = fields.Float(string="Insurance", default=0, tracking=True, digits=(12, 2))
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    default_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Default Account',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", tracking=True, required=True)

    def get_default_service_charge_account(self):
        acc_id = self.env['ir.config_parameter'].sudo().get_param('smif.service_charge_account')
        acc = self.env['account.account'].search([('id', '=', acc_id)])
        return acc

    service_charge_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Service Charge Account', default=get_default_service_charge_account,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", tracking=True)

    def get_default_loan_interest_account(self):
        acc_id = self.env['ir.config_parameter'].sudo().get_param('smif.loan_interest_account')
        acc = self.env['account.account'].search([('id', '=', acc_id)])
        return acc

    loan_interest_account_id = fields.Many2one(
        comodel_name='account.account', check_company=True, copy=False, ondelete='restrict',
        string='Loan Interest Account', default=get_default_loan_interest_account, requered=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", tracking=True, )
    #
    def write(self, vals):
        if vals.__contains__('interest_rate'):
            self.update_all_loan_interest(vals)
        else:
            return super(SmifLoanType, self).write(vals)


    def update_all_loan_interest(self,new_vals):
        params = []
        new_rate=new_vals['interest_rate']

        params.append(('loan_type_id', '=', self.id))
        params.append(('state', '=', 'paid'))
        loans = self.env['smif.loan_request'].search(params)
        for loan in loans:
            if loan.calculated_total_remaining_loan>0:
                loan.interest_rate=new_rate
                loan.recalculateLoanInstallment()

        return super(SmifLoanType, self).write(new_vals)

class SmifLoanInstallment(models.Model):
    _name = 'smif.loan_installment'
    _rec_name = 'installment_number'
    _description = 'Loan Installment Payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _set_loan_payment_amount(self):
        amount = 0
        if (self.is_paid):
            amount = self.loan_paid_amount + self.interest_payment
        else:
            amount = self.principal + self.interest_payment
        return amount

    def _set_saving_amount(self):
        if self.is_paid:
            amount = self.saving_paid_amount
        else:
            amount = self.saving_payment
        return amount

    def _set_penalty_amount(self):
        if self.is_paid:
            amount = self.penalty_paid_amount
        else:
            # Todo: Calculagte penalty based on current date and save to current installment self.penalty_payment
            amount = self.penalty_payment
        return amount

    loan_request_id = fields.Many2one('smif.loan_request', string='Loan', index=True)
    installment_number = fields.Integer(string="Installment Number", required=True)
    saving_payment = fields.Float(string="Saving Payment", required=True, tracking=True,
                                  digits=(12, 2))  # Compulsory Saving Amount
    principal = fields.Float(string="Principal", required=True, tracking=True, digits=(12, 2))  # Monthly Loan Payment
    penalty_payment = fields.Float(string="Penalty Payment", tracking=True, digits=(12, 2))  # Penalty Payment
    interest_payment = fields.Float(string="Interest Payment", required=True, tracking=True,
                                    digits=(12, 2))  # Monthly Interest
    interest_rate = fields.Float(string="Rate", required=True, tracking=True)
    total_installment_payment = fields.Float(string="Total Payment", required=True,
                                             tracking=True, digits=(12, 2))  # Total Monthly Payment
    instalment_date = fields.Date(string="Instalment Date", required=True, default=datetime.today())

    is_paid = fields.Boolean(string="Is Paid", default=False, tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Fields to store actual payments made
    penalty_paid_amount = fields.Float(string="Penalty Paid", tracking=True, digits=(12, 2))  # Actually Penalty Payment
    loan_paid_amount = fields.Float(string="Loan Paid", tracking=True, digits=(12, 2))  # Actually Loan Paid Amount
    saving_paid_amount = fields.Float(string="Saving Paid", tracking=True,
                                      digits=(12, 2))  # Actually Saving Paid Amount
    paid_date = fields.Date(string="Paid Date", tracking=True)

    payment_journal_id = fields.Many2one('account.journal', string='Paid On', check_company=True)
    payment_ref_number = fields.Char('Reference Number')
    payment_check_number = fields.Char('Check Number')
    payment_transaction_note = fields.Text('Note')

    tmp_loan_payment_amount = fields.Float(default=_set_loan_payment_amount, store=False, digits=(12, 2))
    tmp_saving_amount = fields.Float(default=_set_saving_amount, store=False, digits=(12, 2))
    tmp_penalty_amount = fields.Float(default=_set_penalty_amount, store=False, digits=(12, 2))

    calculated_total_payment = fields.Float(compute='_get_payment_sum', digits=(12, 2))

    def _set_next_payable(self):
        # State: Paid, Scheduled, Delayed
        next_payable_set = False
        for rec in self:
            if rec.is_paid:
                rec.is_next_payable = False
            else:
                if next_payable_set == False:
                    rec.is_next_payable = True
                    next_payable_set = True
                else:
                    rec.is_next_payable = False

    is_next_payable = fields.Boolean(store=False, default=False, compute=_set_next_payable)

    def _get_state(self):
        # State: Paid, Scheduled, Delayed
        _state = ''
        for rec in self:
            if rec.is_paid:
                _state = "Paid"
            else:
                if rec.state != 'settled':
                    today = datetime.today().date()
                    if today > rec.instalment_date:
                        _state = "Overdue"
                    else:
                        _state = "Scheduled"

            rec.state = _state

    state = fields.Char(compute=_get_state)

    @api.depends('tmp_loan_payment_amount', 'tmp_saving_amount', 'tmp_penalty_amount')
    def _get_payment_sum(self):
        self.calculated_total_payment = self.tmp_loan_payment_amount + self.tmp_saving_amount + self.tmp_penalty_amount

    # @api.depends( 'saving_paid_amount', 'penalty_paid_amount','interest_payment')
    def _get_total_paid_amount(self):
        for rec in self:
            if rec.is_paid:
                rec.calculated_total_paid_amount = rec.loan_paid_amount + rec.saving_paid_amount + rec.penalty_paid_amount + rec.interest_payment
            else:
                rec.calculated_total_paid_amount = 0

    calculated_total_paid_amount = fields.Float(compute=_get_total_paid_amount)

    def _get_actual_principal(self):
        for rec in self:
            if rec.is_paid:
                rec.calculated_principal = rec.loan_paid_amount
            else:
                rec.calculated_principal = rec.principal

    calculated_principal = fields.Float(compute=_get_actual_principal)

    def _get_actual_saving_paid(self):
        for rec in self:
            if rec.is_paid:
                rec.calculated_saving_paid = rec.saving_paid_amount
            else:
                rec.calculated_saving_paid = rec.saving_payment

    calculated_saving_paid = fields.Float(compute=_get_actual_saving_paid)

    def saveLoanImport(self, pay_amount):
        self.loan_paid_amount = pay_amount

    def write(self, values):
        res = False
        try:

            if self.is_paid == False:
                res = self.saveInstallmentPayment(values)
        except Exception as e:
            raise ValidationError(e)
        return res

    def saveInstallmentPayment(self, values):
        res = False

        payment_check_number = payment_journal_id = paid_date = payment_ref_number = ''
        if 'payment_ref_number' in values:
            payment_ref_number = values['payment_ref_number']
        if 'paid_date' in values:
            paid_date = values['paid_date']
        if 'payment_check_number' in values:
            payment_check_number = values['payment_check_number']
        if 'payment_journal_id' in values:
            payment_journal_id = values['payment_journal_id']
        if 'payment_transaction_note' in values:
            payment_note = values['payment_transaction_note']
        # tmp_penalty_amount, tmp_loan_payment_amount, tmp_saving_amount

        loan_paid_amount = round(self.principal, 2) + round(self.interest_payment, 2)
        saving_paid_amount = round(self.saving_payment, 2)
        penalty_paid_amount = round(self.penalty_payment, 2)

        # Values will be present if modified on the UI, so take the UI data
        if 'tmp_saving_amount' in values:
            saving_paid_amount = values['tmp_saving_amount']
            saving_paid_amount = round(saving_paid_amount, 2)
        if 'tmp_penalty_amount' in values:
            penalty_paid_amount = values['tmp_penalty_amount']
            penalty_paid_amount = round(penalty_paid_amount, 2)
        if 'tmp_loan_payment_amount' in values:
            loan_paid_amount = values['tmp_loan_payment_amount']
            loan_paid_amount = round(loan_paid_amount, 2)

        if saving_paid_amount > 0:
            payment_note = 'Deposit With Loan Payment'
            self.saveDepositWithLoanInstallmentPayment(saving_paid_amount, paid_date, payment_ref_number,
                                                       payment_check_number, payment_note)
        if payment_journal_id != '':
            res = self.createAccountingEntryForInstallmentPayment(payment_journal_id, loan_paid_amount,
                                                                  penalty_paid_amount,
                                                                  saving_paid_amount, paid_date, payment_ref_number)
        else:
            res = True

        actual_loan_paid = loan_paid_amount - round(self.interest_payment,
                                                    2)  # subtract interest amount to get actual paid loan
        if res:
            values.__setitem__('is_paid', True)
            values.__setitem__('loan_paid_amount', actual_loan_paid)
            values.__setitem__('penalty_paid_amount', penalty_paid_amount)
            values.__setitem__('saving_paid_amount', saving_paid_amount)
            values.__setitem__('paid_date', paid_date)

            res = super(SmifLoanInstallment, self).write(values)
        if res:  # Check if over or under payments

            # Check if Over or under payment, to recalculate Payment Installment
            loan_diff = round(actual_loan_paid, 0) - round(self.principal, 2)
            loan_diff = abs(loan_diff)
            if loan_diff >= 1:  # Over or under paid, readjust installment schedule
                self.loan_request_id.recalculateLoanInstallment()
                # self.loan_request_id.recalculateLoanInstallmentFlatRate()

        return res

    def createAccountingEntryForInstallmentPayment(self, payment_journal_id, loan_paid_amount, penalty_paid_amount,
                                                   saving_paid_amount, paid_date, payment_ref_number):
        res = False
        interest_amount = round(self.interest_payment, 2)

        actual_loan_paid = loan_paid_amount - interest_amount  # subtract interest amount to get actual paid loan

        assert actual_loan_paid > 0, "Insufficient Loan Payment, Payment at minimum should be greater than Interest"

        total_payment = actual_loan_paid + interest_amount + penalty_paid_amount + saving_paid_amount

        # Get Chart of Accounts
        loan_receivable_account_id = self.loan_request_id.loan_type_id.default_account_id.id  # Credited
        loan_interest_account_id = self.loan_request_id.loan_type_id.loan_interest_account_id.id  # self.env['ir.config_parameter'].sudo().get_param('smif.loan_interest_account')
        journal = self.env['account.journal'].search([('id', '=', payment_journal_id)])
        cash_account_id = journal.default_account_id.id  # Debited

        # service_charge_amount = 0# self.get_service_charge_amount()

        debit_side = self.prepare_acc_side(total_payment,
                                           cash_account_id, 'debit',
                                           "Total Payment")  # Cash is debited with total amount
        credit_side = self.prepare_acc_side(actual_loan_paid, loan_receivable_account_id, 'credit',
                                            "Loan")  # Cash Account is credited
        credit_side_int = self.prepare_acc_side(interest_amount, loan_interest_account_id, 'credit',
                                                "Interest")  # Cash Account is credited
        lines = [(0, 0, debit_side), (0, 0, credit_side), (0, 0, credit_side_int)]

        if penalty_paid_amount > 0:
            penalty_account_id = self.env['ir.config_parameter'].sudo().get_param('smif.penalty_account')
            penalty_account_id = int(penalty_account_id)
            credit_side = self.prepare_acc_side(penalty_paid_amount, penalty_account_id, 'credit',
                                                "Penalty")  # Penalty is credited
            lines.append((0, 0, credit_side))
        if saving_paid_amount > 0:
            acc = self.loan_request_id.get_saving_account()
            acc_chart_of_account = acc.account_type.default_account_id.id
            credit_side_dep = self.prepare_acc_side(saving_paid_amount, acc_chart_of_account, 'credit',
                                                    "Member Deposit")  # Penalty is credited
            lines.append((0, 0, credit_side_dep))

        res = self.createJournalEntry(lines, payment_journal_id, paid_date, payment_ref_number)

        return res

    def saveInstallmentPaymentFromAccountTransfer(self, from_accounts_code, payment_journal_id, loan_paid_amount,
                                                  penalty_paid_amount, paid_date, payment_ref_number):
        values = {}
        res = self.createAccountingEntryForLoanPaymentFromAccountTransfer(from_accounts_code, payment_journal_id,
                                                                          loan_paid_amount, penalty_paid_amount,
                                                                          paid_date, payment_ref_number)
        actual_loan_paid = loan_paid_amount - round(self.interest_payment,
                                                    2)  # subtract interest amount to get actual paid loan
        if res:
            values.__setitem__('is_paid', True)
            values.__setitem__('loan_paid_amount', actual_loan_paid)
            values.__setitem__('penalty_paid_amount', penalty_paid_amount)
            values.__setitem__('saving_paid_amount', 0)
            values.__setitem__('paid_date', paid_date)
            values.__setitem__('payment_ref_number', payment_ref_number)

            res = super(SmifLoanInstallment, self).write(values)
        if res:  # Check if over or under payments

            # Check if Over or under payment, to recalculate Payment Installment
            loan_diff = round(actual_loan_paid, 0) - round(self.principal, 2)
            loan_diff = abs(loan_diff)
            if loan_diff >= 1:  # Over or under paid, readjust installment schedule
                self.loan_request_id.recalculateLoanInstallment()
                # self.loan_request_id.recalculateLoanInstallmentFlatRate()

        return res

    def saveInstallmentPaymentOnMemberDeactivation(self, loan_paid_amount, interest_amount, penalty_paid_amount,
                                                   paid_date,
                                                   payment_ref_number):
        values = {}
        values.__setitem__('is_paid', True)
        values.__setitem__('loan_paid_amount', loan_paid_amount)
        values.__setitem__('penalty_paid_amount', penalty_paid_amount)

        values.__setitem__('interest_payment', interest_amount)
        values.__setitem__('saving_paid_amount', 0)
        values.__setitem__('paid_date', paid_date)
        values.__setitem__('payment_ref_number', payment_ref_number)

        res = super(SmifLoanInstallment, self).write(values)
        if res:  # Check if over or under payments

            # Check if Over or under payment, to recalculate Payment Installment
            loan_diff = round(loan_paid_amount, 0) - round(self.principal, 2)
            loan_diff = abs(loan_diff)
            if loan_diff >= 1:  # Over or under paid, readjust installment schedule
                self.loan_request_id.recalculateLoanInstallment()
                # self.loan_request_id.recalculateLoanInstallmentFlatRate()

        return res

    def createAccountingEntryForLoanPaymentFromAccountTransfer(self, from_accounts_code, payment_journal_id,
                                                               loan_paid_amount, penalty_paid_amount, paid_date,
                                                               payment_ref_number):
        res = False
        interest_amount = round(self.interest_payment, 2)

        actual_loan_paid = loan_paid_amount - interest_amount  # subtract interest amount to get actual paid loan

        assert actual_loan_paid > 0, "Insufficient Loan Payment, Payment at minimum should be greater than Interest"

        # total_payment = actual_loan_paid + interest_amount + penalty_paid_amount

        # Get Chart of Accounts
        loan_receivable_account_id = self.loan_request_id.loan_type_id.default_account_id.id  # Credited
        loan_interest_account_id = self.loan_request_id.loan_type_id.loan_interest_account_id.id  # self.env['ir.config_parameter'].sudo().get_param('smif.loan_interest_account')

        lines = []
        acc_total = 0
        for acc in from_accounts_code:
            acc_total += from_accounts_code[acc]
            debit_side = self.prepare_acc_side(from_accounts_code[acc],
                                               acc, 'debit',
                                               "Payment From Account")  # Cash is debited with total amount
            lines.append((0, 0, debit_side))
        assert acc_total == loan_paid_amount + penalty_paid_amount, 'Actual Account Total (' + str(
            acc_total) + ') is Different From Loan Payment ' \
                         'Amount (' + str(loan_paid_amount + penalty_paid_amount) + ') '
        credit_side = self.prepare_acc_side(actual_loan_paid, loan_receivable_account_id, 'credit',
                                            "Loan Paid")  # Cash Account is credited
        credit_side_int = self.prepare_acc_side(interest_amount, loan_interest_account_id, 'credit',
                                                "Interest")
        lines.append((0, 0, credit_side))
        lines.append((0, 0, credit_side_int))

        if penalty_paid_amount > 0:
            penalty_account_id = self.env['ir.config_parameter'].sudo().get_param('smif.penalty_account')
            penalty_account_id = int(penalty_account_id)
            credit_side = self.prepare_acc_side(penalty_paid_amount, penalty_account_id, 'credit',
                                                "Penalty")  # Penalty is credited
            lines.append((0, 0, credit_side))
        res = self.createJournalEntry(lines, payment_journal_id, paid_date, payment_ref_number)

        return res

    def saveDepositWithLoanInstallmentPayment(self, saving_amount, paid_date, payment_ref_number,
                                              payment_check_number, payment_note):
        res = False
        member = self.loan_request_id.member_id
        acc = self.loan_request_id.get_saving_account()
        if acc != False:
            values = {'tmp_ref_number': payment_ref_number,
                      'tmp_check_number': payment_check_number,
                      'tmp_transaction_note': payment_note}

            res = member.saveTransaction('deposit', paid_date, acc.id, saving_amount, values)
        return res

    def prepare_acc_side(self, amount, account_code, side, tranName):
        side_vals = {
            'name': tranName,
            'debit': 0.0,
            'credit': 0.0,
            'account_id': account_code,
            # 'tax_line_id': adjustment_type == 'debit' and self.tax_id.id or False,
        }
        side_vals.__setitem__(side, amount)

        return side_vals

    def createJournalEntry(self, lines, journalID, transactionDateTime, reference):
        vals = {
            'journal_id': journalID,
            'date': transactionDateTime,
            'state': 'draft',  # 'posted'
            'auto_post': 'no',
            'ref': reference,
            'line_ids': []
        }
        vals.__setitem__('line_ids', lines)
        move = self.env['account.move'].create(vals)
        return move

    def open_installment_payment(self):
        # for rec in self:
        #     if rec.paid_amount == 0:
        #         rec.paid_amount=3333

        return {
            'name': 'Installment Payment',
            'res_model': 'smif.loan_installment',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_installment_payment_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_installment_payment_view_form').id,
            'target': 'new'
        }


class SmifLoanRequest(models.Model):
    _name = 'smif.loan_request'
    _rec_name = 'loan_type_id'
    _description = 'Loan Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    member_id = fields.Many2one('smif.member',
                                string='Member', index=True)
    loan_type_id = fields.Many2one('smif.loan_type', string='Loan Type', index=True, tracking=True)

    request_date = fields.Date(string="Request Date", required=True, default=datetime.today())
    loan_amount = fields.Monetary(string="Loan Amount", required=True, tracking=True, )

    duration_months = fields.Integer(string="Duration Months", required=False, tracking=True, )
    interest_rate = fields.Float(string="Rate", required=True, tracking=True)
    # penalty_type = fields.Selection(string="Penalty Type",
    #                                 selection=[('percentage', 'Percentage (%)'), ('amount', 'Amount'), ],
    #                                 required=True, tracking=True, )
    # penalty = fields.Float(string="Penalty", required=True, tracking=True, )
    # loan_service_charge = fields.Float(string="Service Charge", required=True)
    processing_date = fields.Date(string="Processing Date", required=False)
    approved_date = fields.Date(string="Approved Date", required=False)
    paid_date = fields.Date(string="Paid Date", required=False)
    reject_date = fields.Date(string="Rejected Date", required=False)
    closed_date = fields.Date(string="Closed Date", required=False)

    insurance_company_ids = fields.Many2one('res.company', string='Insurance Company', tracking=True)
    premium_amount = fields.Monetary(string="Premium Amount", tracking=True, store=True,
                                     compute='_calulate_premium_amount')
    terms_condition = fields.Text(string="Terms of Condition", required=False, tracking=True)
    state = fields.Selection(
        selection=[('draft', 'Registering'), ('requested', 'Requested'),
                   ('approved', 'Approved'), ('paid', 'Paid'), ('rejected', 'Rejected'), ('closed', 'Closed')],
        string="Status", default='draft', tracking=True)
    collateral_ids = fields.One2many('smif.loan_collateral', 'loan_request_id', string='Collateral', )

    loan_installment_ids = fields.One2many('smif.loan_installment', 'loan_request_id', string='Installments')

    person_photo = fields.Image(store=False, related='member_id.person_photo')
    member_id_number = fields.Char(store=False, related='member_id.member_id_number')
    additional_note = fields.Text(store=False, related='member_id.additional_note')
    gender = fields.Selection(string="Gender", store=False, selection=[('male', 'Male'), ('female', 'Female'), ],
                              related='member_id.gender')

    payment_journal_id = fields.Many2one('account.journal', string='Paid On',
                                         check_company=True)

    payment_ref_number = fields.Char('Reference Number')
    payment_check_number = fields.Char('Check Number')
    payment_transaction_note = fields.Text('Note')

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    # Those fileds are for transaction manipulation in memory, not to be saved in database
    tmp_transaction_type = fields.Selection(
        string="Request Type", store=False,
        selection=[('none', 'None'), ('payment', 'Payment'), ('reschedule', 'Reschedule'), ('transfer', 'Transfer'),
                   ('deactivation', 'Deactivation')],
        default='none')
    tmp_loan_selected = fields.Boolean('Select', store=False)

    def _get_total_remaining_loan(self):
        for rec in self:
            total_paid = 0
            paid_installment = 0
            for inst in rec.loan_installment_ids:
                total_paid += inst.loan_paid_amount
                if inst.is_paid: paid_installment += 1
            rec.calculated_total_remaining_loan = rec.loan_amount - total_paid
            rec.paid_installment_count = str(paid_installment) + "/" + str(rec.duration_months)

    calculated_total_remaining_loan = fields.Monetary(compute=_get_total_remaining_loan)
    paid_installment_count = fields.Char(store=False, string="Paid Installments")
    calculated_interest_till_date = fields.Monetary(store=False)

    def _get_member_accounts(self):
        self.member_accounts = self.member_id.member_account_ids

    @api.depends('loan_amount', 'loan_type_id')
    def _calulate_premium_amount(self):
        if self.loan_type_id != None:
            self.premium_amount = self.get_insurance_amount()
        else:
            self.premium_amount = 0

    member_accounts = fields.Float(compute=_get_member_accounts)

    def _get_total_paid_percentage(self):
        for rec in self:
            paid_amnt = 0
            if rec.loan_amount > 0:
                paid_amnt = rec.loan_amount - rec.calculated_total_remaining_loan
                rec.calculated_total_paid_percentage = paid_amnt * 100 / rec.loan_amount
            else:
                rec.calculated_total_paid_percentage = 0

    calculated_total_paid_percentage = fields.Float(string="Paid Percentage", compute=_get_total_paid_percentage,
                                                    digits=(12, 0))

    def _get_loan_calculation_method(self):
        value = self.env['ir.config_parameter'].sudo().get_param('smif.loan_calculation_method')

        return value

    loan_calculation_method = fields.Selection(string="Loan Calculation Method",
                                               default=_get_loan_calculation_method,
                                               config_parameter="smif.loan_calculation_method",
                                               selection=[('flat_balance', 'Flat Balance'),
                                                          ('amortization', 'Amortization'),
                                                          ('declining_balance', 'Declining Balance')], required=False, )

    @api.onchange('loan_type_id')
    def update_loan_type_detail(self):
        if self.loan_type_id:
            # if(self.interest_rate!=0):
            self.interest_rate = self.loan_type_id.interest_rate
            self.duration_months = self.loan_type_id.payment_period
        # else:
        #     self.interest_rate = 0
        #     self.duration_months = 0

    def getNextPayableInstallment(self):
        res = False
        for inst in self.loan_installment_ids:
            if inst.is_paid == False:
                res = inst
                break
        return res

    def getLoanInterestTillDate(self, lastDate):
        unpaid_interest = 0
        for inst in self.loan_installment_ids:
            if inst.is_paid == False:
                if inst.instalment_date <= lastDate:
                    unpaid_interest += inst.interest_payment
        if unpaid_interest == 0:  # Todo: This blook needs to be removed in real case, as inter. depends on payment date not on next installment
            last_int = self.getNextPayableInstallment()
            if last_int:
                unpaid_interest = last_int.interest_payment
        self.calculated_interest_till_date = unpaid_interest
        return unpaid_interest

    def saveLoanPaymentFromAccountTransfer(self, from_accounts_code, payment_journal_id, loan_paid_amount,
                                           penalty_paid_amount, paid_date, payment_ref_number):
        instl = self.getNextPayableInstallment()
        res = False
        if instl:
            res = instl.saveInstallmentPaymentFromAccountTransfer(from_accounts_code, payment_journal_id,
                                                                  loan_paid_amount, penalty_paid_amount, paid_date,
                                                                  payment_ref_number)
        return res

    def saveLoanPaymentOnMemberDeactivation(self, loan_payable, interest, penalty_paid_amount, paid_date,
                                            payment_ref_number):
        instl = self.getNextPayableInstallment()
        res = False
        if instl:

            res = instl.saveInstallmentPaymentOnMemberDeactivation(loan_payable, interest, penalty_paid_amount,
                                                                   paid_date,
                                                                   payment_ref_number)
            if res:
                loan_values = {}
                loan_values.__setitem__('state', 'closed')
                res = super(SmifLoanRequest, self).write(loan_values)
        return res

    def set_to_requested(self):
        if self.loan_amount<=0:
            return show_message('Loan Amount Required', 'Please Provide loan amount' , 'danger')
        if self.collateral_ids.__len__() > 0:
            self.write({'state': 'requested'})
        else:
            return show_message('Collateral Missing','Please Provide Collateral details' , 'danger')


    def progress_button(self):
        return True

    # def set_to_processing(self):
    #     self.write({'state': 'processing', 'processing_date': datetime.today()})

    def set_to_approved(self):
        self.write({'state': 'approved', 'approved_date': datetime.today()})
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': 'Confirmation',
        #         'message': 'Loan Approved',
        #
        #         'sticky': True,
        #     }
        # }

    def set_to_paid(self):
        return self.open_loan_payment_form()

    def reschedulLoan(self):
        return self.open_loan_payment_form()

    def set_to_rejected(self):
        self.write({'state': 'rejected', 'reject_date': datetime.today()})

    def set_to_closed(self):
        self.write({'state': 'closed', 'closed_date': datetime.today()})

    @api.model
    def create(self, values):
        this_loan = super(SmifLoanRequest, self).create(values)
        # this_loan['state'] = 'requested'
        return this_loan

    def write(self, values):
        res = False
        try:
            if self.tmp_transaction_type == 'none' or self.tmp_transaction_type == False:
                res = super(SmifLoanRequest, self).write(values)
            else:
                if self.tmp_transaction_type == 'payment' and self.state != 'paid':
                    res = self.saveLoanPaymentToCustomer(values)
                elif self.tmp_transaction_type == 'reschedule' and self.state == 'paid':
                    res = self.reScheduleLoanInstallment(values)
                    if res:
                        res = super(SmifLoanRequest, self).write(values)
        except Exception as e:
            raise ValidationError(e)
        return res

    def calculateAndCreateLoanInstallment(self, total_loan_amount):
        res = False
        loan_calculation_method = self.loan_calculation_method
        if loan_calculation_method == 'flat_balance':
            res = self.createLoanInstallmentFlatRate(total_loan_amount)
        elif loan_calculation_method == 'amortization':
            res = self.createLoanInstallmentAmortization(total_loan_amount)
        elif loan_calculation_method == 'declining_balance':
            res = self.createLoanInstallmentDecline(total_loan_amount)
        return res

    def recalculateLoanInstallment(self):
        res = False
        loan_calculation_method = self.loan_calculation_method
        if loan_calculation_method == 'flat_balance':
            res = self.recalculateLoanInstallmentFlatRate()
        elif loan_calculation_method == 'amortization':
            res = self.recalculateLoanInstallmentAmortization()
        elif loan_calculation_method == 'declining_balance':
            res = self.recalculateLoanInstallmentDecline()
        return res

    def reScheduleLoanInstallment(self, values):
        res = False
        loan_calculation_method = self.loan_calculation_method
        months_to = 0
        if 'duration_months' in values:
            months_to = values['duration_months']

        if loan_calculation_method == 'flat_balance':
            res = self.reScheduleLoanInstallmentFlatRate(months_to)
        elif loan_calculation_method == 'amortization':
            res = self.reScheduleLoanInstallmentAmortization(months_to)
        elif loan_calculation_method == 'declining_balance':
            res = self.reScheduleLoanInstallmentDecline(months_to)
        return res

    def reScheduleLoanInstallmentAmortization(self, months_to):
        res = False
        total_loan_paid = 0
        paid_inst_counts = 0
        unpaid_inst = []
        for installment in self.loan_installment_ids:
            if installment.is_paid:
                total_loan_paid += installment.loan_paid_amount
                paid_inst_counts += 1
            else:
                unpaid_inst.append(installment)

        total_un_paid_amount = round(self.loan_amount - total_loan_paid, 2)

        new_remaining_intall_count = months_to - paid_inst_counts
        new_principal = round(total_un_paid_amount / new_remaining_intall_count, 2)

        # update existing payments
        updated_count = 0
        last_installment_count = 0
        last_install_date = datetime.today()

        prev_balance = round(self.loan_amount - total_loan_paid, 2)

        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12  # Convert rate to monthly

        _expo_calcul = (1 + int_rate) ** new_remaining_intall_count
        monthly_payment = prev_balance * (int_rate * _expo_calcul / (_expo_calcul - 1))

        saving_amount = self.get_saving_account_amount()
        total_installment_payment = saving_amount + monthly_payment

        for install_to_update in unpaid_inst:
            if (updated_count < new_remaining_intall_count):
                int_amount = int_rate * prev_balance  # Installment Interest
                principal = monthly_payment - int_amount  # Installment principal
                value = {
                    'total_installment_payment': total_installment_payment,
                    'principal': principal,
                    'interest_payment': int_amount
                }
                res = super(SmifLoanInstallment, install_to_update).write(value)
                prev_balance = prev_balance - principal
                updated_count += 1

                if last_installment_count < install_to_update.installment_number:
                    last_installment_count = install_to_update.installment_number
                    last_install_date = install_to_update.instalment_date
            else:
                res = super(SmifLoanInstallment, install_to_update).unlink()

        # add new installments
        if updated_count < new_remaining_intall_count:  # There are more to add
            payment_date = last_install_date
            int_amount = int_rate * prev_balance  # Installment Interest
            principal = monthly_payment - int_amount  # Installment principal

            values = list()
            for i in range(updated_count, new_remaining_intall_count):
                last_installment_count += 1
                payment_date = payment_date + relativedelta(months=1)
                int_amount = int_rate * prev_balance  # Installment Interest
                principal = monthly_payment - int_amount  # Installment principal

                value = {'total_installment_payment': total_installment_payment,
                         'instalment_date': payment_date,
                         'principal': principal,
                         'interest_payment': int_amount,
                         'loan_request_id': self.id,
                         'saving_payment': saving_amount,
                         'is_paid': False,
                         'installment_number': last_installment_count
                         }
                prev_balance = prev_balance - principal
                values.append(value)
            res = self.env['smif.loan_installment'].create(values)

        return res

    def reScheduleLoanInstallmentDecline(self, months_to):
        res = False
        total_loan_paid = 0
        paid_inst_counts = 0
        unpaid_inst = []
        for installment in self.loan_installment_ids:
            if installment.is_paid:
                total_loan_paid += installment.loan_paid_amount
                paid_inst_counts += 1
            else:
                unpaid_inst.append(installment)

        new_remaining_intall_count = months_to - paid_inst_counts

        # update existing payments
        updated_count = 0
        last_installment_count = 0
        last_install_date = datetime.today()

        prev_balance = round(self.loan_amount - total_loan_paid, 2)

        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12  # Convert annual rate to monthly
        saving_amount = self.get_saving_account_amount()

        principal = round(prev_balance / new_remaining_intall_count, 2)

        for install_to_update in unpaid_inst:
            if (updated_count < new_remaining_intall_count):
                int_amount = int_rate * prev_balance  # Installment Interest
                total_installment = principal + int_amount + saving_amount  # Installment principal
                value = {
                    'total_installment_payment': total_installment,
                    'principal': principal,
                    'interest_payment': int_amount
                }
                res = super(SmifLoanInstallment, install_to_update).write(value)
                prev_balance = prev_balance - principal
                updated_count += 1

                if last_installment_count < install_to_update.installment_number:
                    last_installment_count = install_to_update.installment_number
                    last_install_date = install_to_update.instalment_date
            else:
                res = super(SmifLoanInstallment, install_to_update).unlink()

        # add new installments
        if updated_count < new_remaining_intall_count:  # There are more to add
            payment_date = last_install_date

            values = list()
            for i in range(updated_count, new_remaining_intall_count):
                last_installment_count += 1
                payment_date = payment_date + relativedelta(months=1)
                int_amount = int_rate * prev_balance  # Installment Interest
                total_installment = principal + int_amount + saving_amount  # Installment principal

                value = {'total_installment_payment': total_installment,
                         'instalment_date': payment_date,
                         'principal': principal,
                         'interest_payment': int_amount,
                         'loan_request_id': self.id,
                         'saving_payment': saving_amount,
                         'is_paid': False,
                         'installment_number': last_installment_count
                         }
                prev_balance = prev_balance - principal
                values.append(value)
            res = self.env['smif.loan_installment'].create(values)
        return res

    def reScheduleLoanInstallmentFlatRate(self, months_to):
        res = False
        total_loan_paid = 0
        paid_inst_counts = 0
        unpaid_inst = []
        for installment in self.loan_installment_ids:
            if installment.is_paid:
                total_loan_paid += installment.loan_paid_amount
                paid_inst_counts += 1
            else:
                unpaid_inst.append(installment)

        total_un_paid_amount = round(self.loan_amount - total_loan_paid, 2)

        new_remaining_intall_count = months_to - paid_inst_counts
        new_principal = round(total_un_paid_amount / new_remaining_intall_count, 2)

        # update existing payments
        updated_count = 0
        last_installment_count = 0
        last_install_date = datetime.today()

        for install_to_update in unpaid_inst:
            if (updated_count < new_remaining_intall_count):
                total = new_principal + install_to_update.saving_payment + install_to_update.interest_payment
                value = {
                    'total_installment_payment': total,
                    'principal': new_principal,
                }

                res = super(SmifLoanInstallment, install_to_update).write(value)
                updated_count += 1

                if last_installment_count < install_to_update.installment_number:
                    last_installment_count = install_to_update.installment_number
                    last_install_date = install_to_update.instalment_date
            else:
                # extra_installments.append(install_to_update)  # add to removal list of installment
                res = super(SmifLoanInstallment, install_to_update).unlink()

        # add new installments
        if updated_count < new_remaining_intall_count:  # There are more to add
            int_rate = self.interest_rate / 100
            int_rate = int_rate / 12
            saving_amount = self.get_saving_account_amount()
            monthly_interest_payment = total_un_paid_amount * int_rate

            total_installment = saving_amount + new_principal + monthly_interest_payment

            values = list()
            for i in range(updated_count, new_remaining_intall_count):
                last_install_date = last_install_date + relativedelta(months=1)
                last_installment_count += 1
                value = {'total_installment_payment': total_installment,
                         'instalment_date': last_install_date,
                         'principal': new_principal,
                         'interest_payment': monthly_interest_payment,
                         'loan_request_id': self.id,
                         'saving_payment': saving_amount,
                         'is_paid': False,
                         'installment_number': last_installment_count
                         }
                values.append(value)
            res = self.env['smif.loan_installment'].create(values)

        return res


    def recalculateLoanInstallmentFlatRate(self):
        res = False
        total_loan_paid = 0
        paid_inst_counts = 0
        unpaid_inst = []
        for installment in self.loan_installment_ids:
            if installment.is_paid:
                total_loan_paid += installment.loan_paid_amount
                paid_inst_counts += 1
            else:
                unpaid_inst.append(installment)

        total_un_paid_amount = round(self.loan_amount - total_loan_paid, 2)
        unpaid_inst_count = len(unpaid_inst)

        # Todo: This is done only to avoid devision by zero, check if it has logic problem
        if unpaid_inst_count == 0: unpaid_inst_count = 1
        new_principal = round(total_un_paid_amount / unpaid_inst_count, 2)

        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12
        monthly_interest_payment = total_un_paid_amount * int_rate

        for install_to_update in unpaid_inst:
            # if install_to_update.principal != new_principal:
            total_installment = install_to_update.saving_payment + new_principal + monthly_interest_payment
            value = {
                'total_installment_payment': total_installment,
                'principal': new_principal,
                'interest_rate': self.interest_rate,
                'interest_payment': monthly_interest_payment
            }
            res = super(SmifLoanInstallment, install_to_update).write(value)
        return res

    def createLoanInstallmentFlatRate(self, total_loan_amount):
        res = False
        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12
        number_of_installments = self.duration_months
        saving_amount = self.get_saving_account_amount()

        principal = total_loan_amount / number_of_installments
        monthly_interest_payment = total_loan_amount * int_rate

        total_installment = saving_amount + principal + monthly_interest_payment
        payment_date = datetime.today()
        # payment_date=(payment_date.year,payment_date.month,payment_date.day)
        payment_date = payment_date + relativedelta(months=1)  # Todo: This needs to be pushed based on config value
        values = list()
        for i in range(1, number_of_installments + 1):
            payment_date = payment_date + relativedelta(months=1)
            value = {'total_installment_payment': total_installment,
                     'instalment_date': payment_date,
                     'principal': principal,
                     'interest_payment': monthly_interest_payment,
                     'loan_request_id': self.id,
                     'saving_payment': saving_amount,
                     'is_paid': False,
                     'interest_rate':self.interest_rate,
                     'installment_number': i
                     }

            values.append(value)
        res = self.env['smif.loan_installment'].create(values)
        return res

    def recalculateLoanInstallmentAmortization(self):
        res = False
        total_loan_paid = 0
        paid_inst_counts = 0
        unpaid_inst = []
        for installment in self.loan_installment_ids:
            if installment.is_paid:
                total_loan_paid += installment.loan_paid_amount
                paid_inst_counts += 1
            else:
                unpaid_inst.append(installment)

        prev_balance = round(self.loan_amount - total_loan_paid, 2)

        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12  # Convert rate to monthly
        number_of_installments = len(unpaid_inst)

        _expo_calcul = (1 + int_rate) ** number_of_installments
        monthly_payment = prev_balance * (int_rate * _expo_calcul / (_expo_calcul - 1))

        saving_amount = self.get_saving_account_amount()
        total_installment_payment = saving_amount + monthly_payment

        for install_to_update in unpaid_inst:
            int_amount = int_rate * prev_balance  # Installment Interest
            principal = monthly_payment - int_amount  # Installment principal
            # if install_to_update.principal != principal:
            value = {
                'total_installment_payment': total_installment_payment,
                'principal': principal,
                'interest_payment': int_amount,
                'interest_rate': self.interest_rate
            }
            res = super(SmifLoanInstallment, install_to_update).write(value)
            prev_balance = prev_balance - principal
        return res

    def createLoanInstallmentAmortization(self, total_loan_amount):
        res = False
        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12  # Convert annual rate to monthly
        number_of_installments = self.duration_months
        saving_amount = self.get_saving_account_amount()

        prev_balance = total_loan_amount
        _expo_calcul = (1 + int_rate) ** number_of_installments
        monthly_payment = prev_balance * (int_rate * _expo_calcul / (_expo_calcul - 1))

        total_installment = saving_amount + monthly_payment

        payment_date = datetime.today()
        # payment_date=(payment_date.year,payment_date.month,payment_date.day)
        payment_date = payment_date + relativedelta(months=1)  # Todo: This needs to be pushed based on config value
        values = list()
        for i in range(1, number_of_installments + 1):
            payment_date = payment_date + relativedelta(months=1)
            int_amount = int_rate * prev_balance  # Installment Interest
            principal = monthly_payment - int_amount  # Installment principal

            value = {'total_installment_payment': total_installment,
                     'instalment_date': payment_date,
                     'principal': principal,
                     'interest_payment': int_amount,
                     'loan_request_id': self.id,
                     'saving_payment': saving_amount,
                     'interest_rate': self.interest_rate,
                     'is_paid': False,
                     'installment_number': i
                     }
            prev_balance = prev_balance - principal
            values.append(value)
        res = self.env['smif.loan_installment'].create(values)
        return res

    def recalculateLoanInstallmentDecline(self):
        res = False
        total_loan_paid = 0
        paid_inst_counts = 0
        unpaid_inst = []
        for installment in self.loan_installment_ids:
            if installment.is_paid:
                total_loan_paid += installment.loan_paid_amount
                paid_inst_counts += 1
            else:
                unpaid_inst.append(installment)

        prev_balance = round(self.loan_amount - total_loan_paid, 2)

        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12  # Convert rate to monthly
        number_of_installments = len(unpaid_inst)

        principal = round(prev_balance / number_of_installments, 2)

        for install_to_update in unpaid_inst:
            int_amount = int_rate * prev_balance  # Installment Interest
            total_installment = principal + int_amount  # Installment principal
            # if install_to_update.principal != principal:
            value = {
                'total_installment_payment': total_installment,
                'principal': principal,
                'interest_payment': int_amount
            }
            res = super(SmifLoanInstallment, install_to_update).write(value)
            prev_balance = prev_balance - principal
        return res

    def createLoanInstallmentDecline(self, total_loan_amount):
        res = False
        int_rate = self.interest_rate / 100
        int_rate = int_rate / 12  # Convert annual rate to monthly
        number_of_installments = self.duration_months
        saving_amount = self.get_saving_account_amount()

        prev_balance = total_loan_amount
        principal = round(total_loan_amount / number_of_installments, 2)

        payment_date = datetime.today()
        # payment_date=(payment_date.year,payment_date.month,payment_date.day)
        payment_date = payment_date + relativedelta(months=1)  # Todo: This needs to be pushed based on config value
        values = list()
        for i in range(1, number_of_installments + 1):
            payment_date = payment_date + relativedelta(months=1)
            int_amount = int_rate * prev_balance  # Installment Interest
            total_installment = principal + int_amount + saving_amount  # Installment principal

            value = {'total_installment_payment': total_installment,
                     'instalment_date': payment_date,
                     'principal': principal,
                     'interest_payment': int_amount,
                     'loan_request_id': self.id,
                     'interest_rate': self.interest_rate,
                     'saving_payment': saving_amount,
                     'is_paid': False,
                     'installment_number': i
                     }
            prev_balance = prev_balance - principal
            values.append(value)
        res = self.env['smif.loan_installment'].create(values)
        return res

    def saveLoanPaymentToCustomer(self, values):
        # Calculate loan values - Service Charge, - Done
        # Prepare loan repayment schedule - Done
        # Get journal entry items with side - Done
        # Create Accounting Entry for Loan - Done

        payment_note = payment_journal_id = paid_date = payment_check_number = payment_ref_number = ''
        if 'payment_ref_number' in values:
            payment_ref_number = values['payment_ref_number']
        if 'paid_date' in values:
            paid_date = values['paid_date']
        if 'payment_check_number' in values:
            payment_check_number = values['payment_check_number']
        if 'payment_journal_id' in values:
            payment_journal_id = values['payment_journal_id']
        if 'payment_transaction_note' in values:
            payment_note = values['payment_transaction_note']

        res = self.createAccountingEntryForLoanIssuance(payment_journal_id, paid_date, payment_ref_number)
        if res:
            state_val = {'state': 'paid',
                         'paid_date': paid_date,
                         'payment_ref_number': payment_ref_number,
                         'payment_check_number': payment_check_number,
                         'payment_transaction_note': payment_note}
            res = super(SmifLoanRequest, self).write(state_val)

        return res

    def get_insurance_amount(self):
        res = 0
        if self.loan_type_id.insurance_calculation == 'amount':
            res = self.loan_type_id.insurance_amount
        elif self.loan_type_id.insurance_calculation == 'percentage':
            res = self.loan_amount * self.loan_type_id.insurance_amount / 100
        return res

    def get_saving_account(self):
        for acc in self.member_id.member_account_ids:
            if acc.account_type.is_compulsory_account:
                if acc.account_type.is_compulsory_account:
                    return acc
        return False

    def get_saving_account_amount(self):
        res = 0
        acc = self.get_saving_account()
        if acc != False:
            if acc.account_type.minimum_saving_in == 'amount':
                res = acc.account_type.minimum_saving_amount
            elif acc.account_type.minimum_saving_in == 'percentage':
                res = (acc.member_ids.salary * acc.account_type.minimum_saving_amount / 100)
        return res

    def get_service_charge_amount(self):
        res = 0
        if self.loan_type_id.loan_service_charge == 'amount':
            res = self.loan_type_id.service_charge
        elif self.loan_type_id.loan_service_charge == 'percentage':
            res = self.loan_amount * self.loan_type_id.service_charge / 100
        return res

    def createAccountingEntryForLoanIssuance(self, payment_journal_id, paid_date, payment_ref_number):
        res = False

        loan_receivable_account_id = self.loan_type_id.default_account_id.id

        journal = self.env['account.journal'].search([('id', '=', payment_journal_id)])
        cash_account_id = journal.default_account_id.id

        loan_amount = round(self.loan_amount, 2)

        service_charge_amount = round(self.get_service_charge_amount(), 0)
        insurance_amount = round(self.get_insurance_amount(), 0)

        self.calculateAndCreateLoanInstallment(loan_amount)

        debit_side = self.prepare_acc_side(loan_amount, loan_receivable_account_id, 'debit',
                                           "Loan")  # Loan Receivable is debited with total amount
        credit_side = self.prepare_acc_side(loan_amount - (service_charge_amount + insurance_amount), cash_account_id,
                                            'credit',
                                            "Cash")  # Cash Account is credited
        lines = [(0, 0, debit_side), (0, 0, credit_side)]

        if service_charge_amount > 0:
            service_charge_account_id = self.loan_type_id.service_charge_account_id.id
            credit_side = self.prepare_acc_side(service_charge_amount, service_charge_account_id, 'credit',
                                                "Service Charge")  # Cash Account is credited
            lines.append((0, 0, credit_side))
        if insurance_amount > 0:
            loan_insurance_account_id = self.env['ir.config_parameter'].sudo().get_param('smif.insurance_account')
            loan_insurance_account_id = int(loan_insurance_account_id)
            credit_side = self.prepare_acc_side(insurance_amount, loan_insurance_account_id, 'credit',
                                                "Insurance")  # Cash Account is credited
            lines.append((0, 0, credit_side))

        res = self.createJournalEntry(lines, payment_journal_id, paid_date, payment_ref_number)

        return res

    def prepare_acc_side(self, amount, account_code, side, tranName):
        side_vals = {
            'name': tranName,
            'debit': 0.0,
            'credit': 0.0,
            'account_id': account_code,
            # 'tax_line_id': adjustment_type == 'debit' and self.tax_id.id or False,
        }
        side_vals.__setitem__(side, amount)

        return side_vals

    def createJournalEntry(self, lines, journalID, transactionDateTime, reference):
        vals = {
            'journal_id': journalID,
            'date': transactionDateTime,
            'state': 'draft',  # 'posted'
            'auto_post': 'no',
            'ref': reference,
            'line_ids': []
        }

        vals.__setitem__('line_ids', lines)
        move = self.env['account.move'].create(vals)
        return move

    def open_loan_payment_form(self):
        # self.tmp_transaction_type == 'payment'
        return {
            'name': 'Loan Payment',
            'res_model': 'smif.loan_request',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_loan_paid_view_form', 'tmp_transaction_type': 'payment',
                        'default_tmp_transaction_type': 'payment'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_loan_paid_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_loan_paid_view_form').id,
            'target': 'new'
        }

    def open_loan_reschedule_form(self):
        # self.tmp_transaction_type == 'payment'
        return {
            'name': 'Loan Reschedule',
            'res_model': 'smif.loan_request',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_loan_reschedule_view_form', 'tmp_transaction_type': 'reschedule',
                        'default_tmp_transaction_type': 'reschedule'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_loan_reschedule_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_loan_reschedule_view_form').id,
            'target': 'new'
        }


class SmifLoanCollateral(models.Model):
    _name = 'smif.loan_collateral'
    _description = 'Loan Collateral'
    loan_request_id = fields.Many2one('smif.loan_request', string='Parent', index=True)

    collateral_type = fields.Selection(string="Collateral Type",
                                       selection=[('salary', 'Salary'), ('vehicle', 'Vehicle'),
                                                  ('house', 'House'), ], required=True, )
    # Salary Collateral Detail
    name = fields.Char(string="Name", required=True, )
    organization_name = fields.Char(string="Organization", required=False, )
    income_amount = fields.Float(string="Income Amount", required=True, digits=(12, 2))

    # Other collateral types details to be added later
