import base64

from datetime import datetime, date

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.modules import get_module_resource


class SmifMember(models.Model):
    # _name = 'smif.member'
    _name = 'smif.member'

    _rec_name = 'fullName'
    _description = 'Smart Microfinance Member'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # _inherits = {'res.partner': 'partner_id'}
    # partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade')

    @api.model
    def _default_image(self):
        image_path = get_module_resource('smif', 'static/src/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    member_id_number = fields.Char(string="Member ID", )
    user_id = fields.Many2one('res.users', string='User Account', store=True, readonly=False)

    title_id = fields.Many2one('res.partner.title', string='Title', store=True, readonly=False)
    fullName = fields.Char(string="Full Name", required=True, tracking=True)  # This is Member Full Name
    gender = fields.Selection(string="Gender", selection=[('male', 'Male'), ('female', 'Female'), ],
                              required=True, default='male')
    marital = fields.Selection([('single', 'Single'), ('married', 'Married'), ('widower', 'Widower'),
                                ('divorced', 'Divorced'), ], string='Marital Status', default='single',
                               required=True, tracking=True)
    dob = fields.Date(string="Date Of Birth", required=True, tracking=True)
    country_id = fields.Many2one('res.country', 'Nationality', tracking=True, default=69)
    education_level = fields.Selection(
        [('none', 'None'), ('elementary', 'Elementary'), ('highSchool', 'High School'), ('certificate', 'Certificate'),
         ('diploma', 'Diploma'),
         ('degree', 'Degree'), ('masters', 'Masters'), ('doctorate', 'Doctorate'), ],
        string='Education Level', default='none', required=True, tracking=True)
    occupation = fields.Char(string="Occupation", )
    address_id = fields.Many2one(
        'smif.address',
        string='Address',
        ondelete='cascade',
        help="Select Member Address", tracking=True,
    )
    # address_id = fields.Many2one(
    #     'res.partner', 'Address', help='Enter here the private address of the member.',
    #     tracking=True, )  # This will be modified to our country way of addressing.

    # position = fields.Selection([('none', 'None'), ('LoanBoard', 'Loan Board'), ('Other', 'Other'), ],
    #                             string='Position', help='Select if Member as other assigned position at the company',
    #                             default='none', tracking=True)
    #company_id = fields.Many2one('res.company', 'Company')
    department_id = fields.Many2one('hr.department', 'Department',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    job_title_id = fields.Many2one('hr.job', 'Job Title', help='Job Title of Member in company working at.')
    pay_zone_id = fields.Many2one('smif.pay_zone', string='Pay Zone', index=True, tracking=True)

    work_phone = fields.Char('Work Phone')
    mobile_phone = fields.Char('Mobile')
    email_address = fields.Char('Email')
    national_id = fields.Char('National ID')

    # family_count = fields.Integer(string="Number of Family", required=False, )
    active = fields.Boolean('Active', default=True, store=True, )

    relation_ship = fields.Selection([('child', 'Child'), ('spouse', 'Spouse'), ('father', 'Father'),
                                      ('mother', 'Mother'), ('other', 'Other')], string='Relation Ship',
                                     default='other', required=False, tracking=False)

    # parent_id = fields.Many2one('smif.member', string='Parent', index=True)
    # parent_name = fields.Char(related='parent_id.name', readonly=True, string='Parent name')
    family_ids = fields.One2many('smif.family', 'parent_member_id', string='Family', )
    additional_note = fields.Text(string='Additional Note', tracking=True)
    person_photo = fields.Image(default=_default_image, store=True, attachment=True)
    shares_purchased_ids = fields.One2many('smif.member_shares', 'member_id', string='Member Shares', tracking=True)
    member_account_ids = fields.One2many('smif.member_account', 'member_ids', string='Member Accounts', tracking=True)
    member_loan_ids = fields.One2many('smif.loan_request', 'member_id', string='Member Loans', tracking=True)
    signature = fields.Image(default=_default_image, store=True, attachment=True, tracking=True)

    salary = fields.Monetary(string="Salary", required=True, default=0, tracking=True)
    additional_income = fields.Monetary(string="Additional Income", required=True, default=0, tracking=True)

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    is_committee_member = fields.Boolean(string="Is Committee Member", default=False, )
    position_in_committee = fields.Many2one('hr.job', 'Position in Committee', help='Role of member in committee.',
                                            store=True, readonly=False)

    # Those fileds are for transaction manipulation in memory, not to be saved in database
    tmp_transfer_type = fields.Selection(string='Transfer Type',
                                         selection=[('account_to_account', 'Own Account'),
                                                    ('account_to_loan', 'Account to Loan')])
    tmp_transaction_type = fields.Selection(
        string="Transaction Type",
        selection=[('none', 'none'), ('deposit', 'Deposit'), ('withdrawal', 'Withdrawal'), ('transfer', 'Transfer'), (
            'deactivation', 'Deactivation')],
        store=False, help="Select Transaction Type", default='none')

    tmp_journal_id = fields.Many2one('account.journal', string='Paid On',
                                     check_company=True, required=True)

    tmp_ref_number = fields.Char('Reference Number', store=False)
    tmp_check_number = fields.Char('Check Number', store=False)
    tmp_transaction_note = fields.Char('Note', store=False)

    is_member_id_auto_generated = fields.Boolean(string='Id Setting', compute='get_id_auto_generate_setting')

    tmp_transfer_to_account_id = fields.Many2one('smif.member_account', string='Transfer To Account',
                                                 )
    # Those values will be set only if member is deactivating
    deactivation_date = fields.Date(string='Deactivation Date', default=datetime.now())
    deactivation_remark = fields.Text(string='Deactivation Remark')
    deactivation_ref_number = fields.Char('Reference Number', store=True)
    deactivation_check_number = fields.Char('Check Number', store=True)
    deactivation_journal_id = fields.Many2one('account.journal', string='Paid On',
                                              check_company=True, required=False)

    total_account_balance = fields.Monetary('Account Total', store=True)
    total_share = fields.Monetary('Share Total', store=True)
    total_loan_remaining = fields.Monetary('Total Loan', store=True)
    total_loan_interest = fields.Monetary('Total Interest', store=True)
    total_loan_penalty = fields.Monetary('Total Penalty', store=True)
    saving_loan_diff_payable = fields.Monetary('Saving and Loan Diff',
                                               store=True)  # < 0 Member must pay, > 0 Must be paid to member, =0 no payment transaction
    member_total_balance = fields.Monetary('Member Total Balance', store=True)
    loan_payable_total = fields.Monetary('Loan Payable Total', store=True)

    # Mobile Field to be unique
    @api.constrains('member_id_number')
    def check_member_id_number_unique(self):
        members_count = self.search_count([('member_id_number', '=', self.member_id_number), ('id', '!=', self.id)])
        print(members_count)
        if members_count > 0:
            raise ValidationError("Member with given ID Number Exists. Member Id Should not be duplicated.")

    def get_member_account_by_type(self, acc_type):
        for acc in self.member_account_ids:
            if acc.account_type.id == acc_type.id and acc.is_active:
                return acc
        return False

    def get_member_loan_by_type(self, loan_type):
        for ln in self.member_loan_ids:
            if ln.loan_type_id.id == loan_type.id and ln.state == 'paid':
                if ln.calculated_total_remaining_loan>0:
                    return ln
        return False

    def calculate_member_deactivation(self, dateTime):
        if self.active:  # Calculate only if member is active
            for rec in self:
                acc_tootal = 0
                share_total = 0
                loan_total = 0
                interest_total = 0
                loan_penalty = 0
                for acc in rec.member_account_ids:
                    acc_tootal += acc.current_balance
                for share in rec.shares_purchased_ids:
                    share_total += share.total_amount
                for loan in rec.member_loan_ids:
                    loan_total += loan.calculated_total_remaining_loan
                    interest_total += loan.getLoanInterestTillDate(dateTime)
                    loan_penalty += 0  # Todo: Calculate total loan Penalty
                rec.total_account_balance = acc_tootal
                rec.total_share = share_total
                rec.member_total_balance = acc_tootal + share_total

                rec.total_loan_remaining = loan_total
                rec.total_loan_interest = interest_total
                rec.total_loan_penalty = loan_penalty
                rec.loan_payable_total = loan_total + interest_total + loan_penalty

                rec.saving_loan_diff_payable = rec.member_total_balance - rec.loan_payable_total

    def _set_default_registration_fee(self):
        res = self.env['ir.config_parameter'].sudo().get_param('smif.registration_fee')
        return res

    registration_fee = fields.Monetary(string="Registration Fee", required=True, default=_set_default_registration_fee)

    @api.model
    def create(self, values):
        res = False

        if self.get_id_auto_generate_setting():
            id_Val = str(self.env['ir.sequence'].next_by_code('member_id_sec'))
            values['member_id_number'] = id_Val
        else:
            assert ('member_id_number' in values and values[
                'member_id_number']), 'Member ID Is Required. Please Enter Member ID'

            # mem_id=values['member_id_number']
            # params = []
            # params.append(('member_id_number', '=', mem_id))
            # mem = self.env['smif.member'].search(params)
            # assert mem.__len__()==0,'Member ID Number Should be unique, Please provide unique number'


        res = super(SmifMember, self).create(values)
        if res:
            reg_fee = self.registration_fee
            if 'registration_fee' in values:
                reg_fee = values['registration_fee']

            if reg_fee > 0:
                res2 = self.savePaymentsWithRegistration(values, res, reg_fee)

        return res

    def write(self, values):
        res = False
        # message=""
        try:
            if self.tmp_transaction_type == 'none':
                res = super(SmifMember, self).write(values)
                if res:
                    if 'member_account_ids' in values or 'shares_purchased_ids' in values:
                        res2 = self.savePaymentsWithRegistration(values, self, 0)
                    # message="Member Saved Successfully"
            else:
                if self.tmp_transaction_type == 'deposit':
                    res = self.saveDepositTransaction(values)
                    # message = "Member Deposit Saved Successfully"
                elif self.tmp_transaction_type == 'withdrawal':
                    res = self.saveWithdrawalTransaction(values)
                    # message = "Account Withdrawal Saved Successfully"
                elif self.tmp_transaction_type == 'transfer':
                    res = self.saveTransferTransaction(values)
                    # message = "Account Transfer Saved Successfully"
                elif self.tmp_transaction_type == 'deactivation':
                    res = self.saveMemberDeativation(values)
                    # message = "Account Transfer Saved Successfully"
        except Exception as e:
            raise ValidationError(e)
        return res
        # if res:
        #     res =self.get_error_message(message)
        # return {
        #     'type': 'ir.actions.client',
        #     'tag': 'display_notification',
        #     'params': {
        #         'title': 'The following replenishment order has been generated',
        #         'message': '%s',
        #
        #         'sticky': False,
        #     }
        # }

    def get_error_message(self, message_text):
        message_id = self.env['smif.message'].create({'message': message_text})
        return {
            'name': 'Error',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'smif.message',
            'res_id': message_id.id,
            'target': 'new'
        }

    def show_form(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'The following replenishment order has been generated',
                'message': '%s',

                'sticky': False,
            }
        }

    def saveMemberDeativation(self, values):
        res = False
        if self.active:

            transactionDateTime = datetime.now()
            total_transfer_amount = 0
            refNumber = ''
            deactivation_remark = ''
            deactivation_ref_number = ''

            if 'deactivation_journal_id' in values:
                journalID = values['deactivation_journal_id']
            else:
                journalID = self.deactivation_journal_id.id

            if 'deactivation_remark' in values:
                deactivation_remark = values['deactivation_remark']
            if 'deactivation_ref_number' in values:
                deactivation_ref_number = values['deactivation_ref_number']
            if deactivation_ref_number == '':
                deactivation_ref_number = self.member_id_number

            if 'deactivation_date' in values:
                transactionDateTime = datetime.strptime(values['deactivation_date'], '%Y-%m-%d').date()

            memberAccount = self.member_account_ids

            debited_accounts = {}
            # Deduct all accounts, and gettal account balance
            for acct in memberAccount:
                transfer_amount = acct.current_balance
                total_transfer_amount += transfer_amount
                if transfer_amount > 0:
                    res = self.saveTransaction('withdrawal', transactionDateTime, acct.id, transfer_amount,
                                               values)
                    if res:
                        acct.is_active = False
                        chOfAcc = acct.account_type.default_account_id.id
                        if debited_accounts.__contains__(chOfAcc):
                            debited_accounts[chOfAcc] += transfer_amount
                        else:
                            debited_accounts[chOfAcc] = transfer_amount
            # Deduct all shares and get all total share
            shares = self.shares_purchased_ids
            for share in shares:
                transfer_amount = share.total_amount
                total_transfer_amount += transfer_amount
                if transfer_amount > 0:
                    share.is_active = False
                    chOfAcc_Share = share.share.default_account_id.id
                    if debited_accounts.__contains__(chOfAcc_Share):
                        debited_accounts[chOfAcc_Share] += transfer_amount
                    else:
                        debited_accounts[chOfAcc_Share] = transfer_amount

            member_loans = self.member_loan_ids
            credit_side_accounts = {}

            penalty_account_id = self.env['ir.config_parameter'].sudo().get_param('smif.penalty_account')
            penalty_account_id = int(penalty_account_id)
            total_loan_paid_amount = 0
            for loan in member_loans:
                if loan.state == 'paid':
                    penalty_paid_amount = 0  # Todo: Calculate and penality
                    loan_payable = loan.calculated_total_remaining_loan
                    interest = loan.getLoanInterestTillDate(transactionDateTime)
                    res = loan.saveLoanPaymentOnMemberDeactivation(loan_payable, interest, penalty_paid_amount,
                                                                   transactionDateTime,
                                                                   refNumber)
                    if res:
                        total_loan_paid_amount += loan_payable + interest + penalty_paid_amount
                        chOfAcc_Loan = loan.loan_type_id.default_account_id.id
                        chOfAccInt = loan.loan_type_id.loan_interest_account_id.id

                        if credit_side_accounts.__contains__(chOfAcc_Loan):
                            credit_side_accounts[chOfAcc_Loan] += loan_payable
                        else:
                            credit_side_accounts[chOfAcc_Loan] = loan_payable

                        if interest > 0:
                            if credit_side_accounts.__contains__(chOfAccInt):
                                credit_side_accounts[chOfAccInt] += interest
                            else:
                                credit_side_accounts[chOfAccInt] = interest

                        if penalty_paid_amount > 0:
                            if credit_side_accounts.__contains__(penalty_account_id):
                                credit_side_accounts[penalty_account_id] += penalty_paid_amount
                            else:
                                credit_side_accounts[penalty_account_id] = penalty_paid_amount

            journal = self.env['account.journal'].search([('id', '=', journalID)])
            cash_journal_code = journal.default_account_id.id

            diff_2 = total_transfer_amount - total_loan_paid_amount
            diff_abs = abs(self.saving_loan_diff_payable)
            if self.saving_loan_diff_payable > 0:  # Member has to pay extra amount, credit cash, More Deposit
                if credit_side_accounts.__contains__(cash_journal_code):
                    credit_side_accounts[cash_journal_code] += diff_abs
                else:
                    credit_side_accounts[cash_journal_code] = diff_abs

            elif self.saving_loan_diff_payable < 0:  # Member will be paid extra amount, debit cash, More Loan
                if debited_accounts.__contains__(cash_journal_code):
                    debited_accounts[cash_journal_code] += diff_abs
                else:
                    debited_accounts[cash_journal_code] = diff_abs
            lines = []
            for d_key in debited_accounts.keys():
                debit_side = self.prepare_acc_side(debited_accounts[d_key],
                                                   d_key, 'debit',
                                                   "Member Deactivation")
                lines.append((0, 0, debit_side))

            for c_key in credit_side_accounts.keys():
                credit_side = self.prepare_acc_side(credit_side_accounts[c_key],
                                                    c_key, 'credit',
                                                    "Member Deactivation")
                lines.append((0, 0, credit_side))
            res = self.createJournalEntry(lines, journalID, transactionDateTime, deactivation_ref_number)

            if res:
                values.__setitem__('active', False)
                values.__setitem__('deactivation_date', transactionDateTime)
                values.__setitem__('deactivation_remark', deactivation_remark)
                values.__setitem__('deactivation_journal_id', journalID)
                values.__setitem__('deactivation_ref_number', deactivation_ref_number)

                values.__setitem__('total_account_balance', self.total_account_balance)
                values.__setitem__('total_share', self.total_share)
                values.__setitem__('total_loan_remaining', self.total_loan_remaining)
                values.__setitem__('saving_loan_diff_payable', self.saving_loan_diff_payable)

                res = super(SmifMember, self).write(values)
        return res

    def savePaymentsWithRegistration(self, values, savedMember, reg_fee):
        res = False
        initial_depo = 0
        # reg_fee = savedMember.registration_fee
        if 'tmp_journal_id' in values:
            journalID = values['tmp_journal_id']
        else:
            journalID = self.tmp_journal_id.id

        journal = self.env['account.journal'].search([('id', '=', journalID)])
        journal_code = journal.default_account_id.id

        acc_credit_sides = {}
        total_init_depo = 0
        acc_labels = []

        if not ('tmp_transaction_date' in values):
            transactionDateTime = datetime.now()
        else:
            transactionDateTime = values['tmp_transaction_date']

        refNumber = ''
        if 'tmp_ref_number' in values:
            refNumber = values['tmp_ref_number']
        if refNumber == '':
            refNumber = self.member_id_number

        # if 'registration_fee' in values:
        #     reg_fee = values['registration_fee']
        depositAccountsAmount = savedMember.member_account_ids  # values['member_account_ids']
        for acc in depositAccountsAmount:
            initial_depo = acc.initial_deposit
            if initial_depo > 0 and not acc.is_accounting_set:  # if there is initial deposit
                # account = self.env['smif.member_account'].search([('id', '=', acc[1])])

                saving_account_code = acc.account_type.default_account_id.id  # Get Chart of account code by saving account type

                total_init_depo += initial_depo
                if acc_credit_sides.__contains__(saving_account_code):
                    val = acc_credit_sides[saving_account_code]
                    acc_credit_sides[saving_account_code] = initial_depo + val

                else:
                    acc_credit_sides[saving_account_code] = initial_depo
                    acc_labels.append('Initial Deposit')

                res = self.saveTransaction('deposit', transactionDateTime, acc.id, initial_depo, values)
                acc.is_accounting_set = True
        total_share = 0
        for share in savedMember.shares_purchased_ids:
            share_amount = share.total_amount
            if share_amount > 0 and not share.is_accounting_set:
                share_account_code = share.share.default_account_id.id
                total_share += share_amount
                if acc_credit_sides.__contains__(share_account_code):
                    val = acc_credit_sides[share_account_code]
                    acc_credit_sides[share_account_code] = share_amount + val
                else:
                    acc_credit_sides[share_account_code] = share_amount
                    acc_labels.append('Share Purchase')
                share.is_accounting_set = True
                share.share.save_shares_sales(share.purchased_quantity)

        amount = total_init_depo + reg_fee + total_share
        if amount > 0:  # If there is any amount to record journal entry
            debit_side = self.prepare_acc_side(amount, journal_code, 'debit',
                                               'Member Registration')  # Cash account is debited
            lines = [(0, 0, debit_side)]

            if reg_fee > 0:  # If there is registration fee passed
                reg_fee_account = self.env['ir.config_parameter'].sudo().get_param('smif.reg_fee_account')
                credit_side_reg_fee = self.prepare_acc_side(reg_fee, int(reg_fee_account), 'credit', 'Registration Fee')
                lines.append((0, 0, credit_side_reg_fee))

            label_index = 0
            label = ''
            for acc_code in acc_credit_sides.keys():
                if len(acc_labels) > label_index:
                    label = acc_labels.__getitem__(label_index)
                credit_side = self.prepare_acc_side(acc_credit_sides[acc_code], acc_code, 'credit',
                                                    label)  # Saving Account is credited
                lines.append((0, 0, credit_side))
                label_index += 1
            res = self.createJournalEntry(lines, journalID, transactionDateTime, refNumber)
        return res

    def saveDepositTransaction(self, values):
        res = False
        transactionDateTime = datetime.now()

        if 'member_account_ids' in values:  # check if account types of member are passed for transaction, else no transaction
            depositAccountsAmount = values['member_account_ids']
            for acc in depositAccountsAmount:
                if isinstance(acc[2], dict) and 'tmp_transaction_amount' in acc[
                    2]:  # check if deposit amount is passed from ui
                    amount = acc[2]['tmp_transaction_amount']
                    if not ('tmp_transaction_date' in acc[2]):
                        transactionDateTime = datetime.now()
                    else:
                        transactionDateTime = acc[2]['tmp_transaction_date']
                    res = self.saveTransaction('deposit', transactionDateTime, acc[1], amount, values)
                    # newTranID=res.id
                    refNumber = ''
                    if 'tmp_ref_number' in values:
                        refNumber = values['tmp_ref_number']
                    if refNumber == '':
                        refNumber = self.member_id_number
                    if 'tmp_journal_id' in values:
                        journalID = values['tmp_journal_id']
                    else:
                        journalID = self.tmp_journal_id.id

                    if res:
                        res = self.createAccountingEntryForDeposit(amount, journalID, acc[1], transactionDateTime,
                                                                   refNumber)
        return res

    def createAccountingEntryForDeposit(self, amount, journalID, savingAccountID, transactionDateTime, tranReference):
        res = False

        account = self.env['smif.member_account'].search([('id', '=', savingAccountID)])

        tranName = 'Deposit to - ' + account.account_number
        saving_account_code = account.account_type.default_account_id.id  # Get Chart of account code by saving account type
        # Journal's account code

        journal = self.env['account.journal'].search([('id', '=', journalID)])
        journal_code = journal.default_account_id.id

        debit_side = self.prepare_acc_side(amount, journal_code, 'debit', tranName)  # Cash account is debited
        credit_side = self.prepare_acc_side(amount, saving_account_code, 'credit',
                                            tranName)  # Saving Account is credited
        lines = [(0, 0, debit_side), (0, 0, credit_side)]
        res = self.createJournalEntry(lines, journalID, transactionDateTime, tranReference)

        return res

    def createAccountingEntryForWithdrawal(self, requested_amount, service_charge, journalID, savingAccountID,
                                           transactionDateTime, tranReference):
        res = False

        account = self.env['smif.member_account'].search([('id', '=', savingAccountID)])

        tranName = 'Withdrawal from - ' + account.account_number
        saving_account_code = account.account_type.default_account_id.id  # Get Chart of account code by saving account type
        # Journal's account code

        journal = self.env['account.journal'].search([('id', '=', journalID)])
        journal_code = journal.default_account_id.id

        debit_side = self.prepare_acc_side(requested_amount + service_charge, saving_account_code, 'debit',
                                           tranName)  # Saving account is debited with total (amount + service charge)
        credit_side = self.prepare_acc_side(requested_amount, journal_code, 'credit',
                                            tranName)  # Cash Account is credited
        lines = [(0, 0, debit_side), (0, 0, credit_side)]

        if service_charge > 0:
            service_charge_account = account.account_type.service_charge_account_id.id
            credit_side = self.prepare_acc_side(service_charge, service_charge_account, 'credit',
                                                tranName)  # Cash Account is credited
            lines.append((0, 0, credit_side))

        res = self.createJournalEntry(lines, journalID, transactionDateTime, tranReference)

        return res

    def createAccountingEntryForAccountTransfer(self, requested_amount, journalID, from_accounts_code, to_account_id,
                                                transactionDateTime, tranReference):
        res = False

        to_account = self.env['smif.member_account'].search([('id', '=', to_account_id)])

        lines = []
        acc_total = 0
        for acc in from_accounts_code:
            acc_total += from_accounts_code[acc]
            debit_side = self.prepare_acc_side(from_accounts_code[acc],
                                               acc, 'debit',
                                               "Transfer From")  # Cash is debited with total amount
            lines.append((0, 0, debit_side))
        assert acc_total == requested_amount, 'Total Transfer Amount and Requested amount not equal'
        chart_of_account_to = to_account.account_type.default_account_id.id  # Get Chart of account code by saving account type

        credit_side = self.prepare_acc_side(requested_amount, chart_of_account_to, 'credit',
                                            'Transfer To')  # Cash Account is credited
        lines.append((0, 0, credit_side))

        res = self.createJournalEntry(lines, journalID, transactionDateTime, tranReference)

        return res

    def hasMemberAccountEnoughBalanceToWithdraw(self, account_id, total_amount):
        result = False
        account = self.env['smif.member_account'].search([('id', '=', account_id)])
        assert account.current_balance >= total_amount, "Insufficient Balance to withdraw"
        result = True
        return result

    def getWithdrawalServiceChargeAmount(self, accountID, requestedAmount):
        serviceCharge = 0.0
        account = self.env['smif.member_account'].search([('id', '=', accountID)])
        if (account.account_type.withdrawal_service_charge == 'amount'):
            serviceCharge = account.account_type.service_charge
        elif (account.account_type.withdrawal_service_charge == 'percentage'):
            serviceCharge = requestedAmount * account.account_type.service_charge / 100
        else:
            serviceCharge = 0.0

        return serviceCharge

    def saveTransferTransaction(self, values):

        res = False
        transactionDateTime = datetime.now()
        transfer_to_account = 0
        transfer_from_count = 0
        transfer_to_count = 0
        total_transfer_amount = 0

        transaction_type = 'account_to_account'
        if 'tmp_transfer_type' in values:
            transaction_type = values['tmp_transfer_type']

        memberAccount = values['member_account_ids']
        transfer_from_accounts = {}
        for acct in memberAccount:
            if isinstance(acct[2], dict):
                if 'tmp_transfer_from_account' in acct[2]:
                    if acct[2]['tmp_transfer_from_account'] == True:
                        transfer_amount = acct[2]['tmp_transaction_amount']
                        from_account = acct[1]

                        assert self.hasMemberAccountEnoughBalanceToWithdraw(from_account,
                                                                            transfer_amount), 'Account Has No Enough Balance To Transfer ' + str(
                            transfer_amount)

                        transfer_from_accounts[from_account] = transfer_amount
                        if 'tmp_transaction_date' in acct[2]:
                            transactionDateTime = acct[2]['tmp_transaction_date']
                        transfer_from_count += 1
                        total_transfer_amount += transfer_amount
                elif 'tmp_transfer_to_account' in acct[2]:
                    if acct[2]['tmp_transfer_to_account'] == True:
                        transfer_to_account = acct[1]
                        transfer_to_count += 1
        assert transfer_from_count > 0, 'Transfer from account is not selected, please specify at least one account to transfer from.'

        if transaction_type == 'account_to_loan':
            transfer_to_loan = 0
            loan_remaining_amount = 0
            member_loans = values['member_loan_ids']
            for loan in member_loans:
                if isinstance(loan[2], dict):
                    if 'tmp_loan_selected' in loan[2]:
                        if loan[2]['tmp_loan_selected'] == True:
                            transfer_to_loan = loan[1]
                            loan_req = self.env['smif.loan_request'].search([('id', '=', transfer_to_loan)])
                            loan_remaining_amount = loan_req.calculated_total_remaining_loan
            assert transfer_to_loan > 0, 'Please select loan to transfer to'
            assert loan_remaining_amount >= total_transfer_amount, 'Transfer Amount (' + str(
                total_transfer_amount) + ') Exceeds Loan Remaining Amount (' + str(loan_remaining_amount) + ')'

        refNumber = self.member_id_number
        # Search for Miscellaneous Accounts
        journalID = 0
        journal = self.env['account.journal'].search([])
        for jor in journal:
            if 'Miscellaneous' in jor.name:
                journalID = jor.id
                break
        assert journalID > 0, 'Cant Find Miscellaneous Journal, Please Configure it.'

        total_withdrawn_amount = 0
        from_accounts_code = {}

        for acc in transfer_from_accounts.keys():  # Get and map member account to chart of account, and sum if chart of account is same
            assert transfer_to_account != int(
                acc), "Can't Transfer Between Same Account. Please Select Different Accounts."
            with_draw = transfer_from_accounts[acc]

            res = self.saveTransaction('withdrawal', transactionDateTime, acc, with_draw,
                                       values)
            if res:
                total_withdrawn_amount += with_draw
                account = self.env['smif.member_account'].search([('id', '=', acc)])
                chOfAcc = account.account_type.default_account_id.id
                if from_accounts_code.__contains__(chOfAcc):
                    from_accounts_code[chOfAcc] += transfer_from_accounts[acc]
                else:
                    from_accounts_code[chOfAcc] = transfer_from_accounts[acc]

        assert total_withdrawn_amount == total_transfer_amount, 'Unable to withdraw from all selected account, Unbalanced Withdrawn and Transfer Amount'

        if transaction_type == 'account_to_account':  # Withdrawal successful, deposit to account to transfer to
            assert transfer_to_count > 0, 'Account to transfer to is not selected, please select one account to transfer to.'
            assert transfer_to_count == 1, "Transfer to multiple account is not possible. Please select exactly one account to transfer to."

            if self.saveTransaction('deposit', transactionDateTime, transfer_to_account,
                                    total_transfer_amount, values):
                res = self.createAccountingEntryForAccountTransfer(total_transfer_amount, journalID, from_accounts_code,
                                                                   transfer_to_account,
                                                                   transactionDateTime,
                                                                   refNumber)
        elif transaction_type == 'account_to_loan':
            penalty_paid_amount = 0  # Todo: Get Penalyt Amount
            loan_req.saveLoanPaymentFromAccountTransfer(from_accounts_code, journalID, total_transfer_amount,
                                                        penalty_paid_amount, transactionDateTime,
                                                        refNumber)
        return res

    def saveWithdrawalTransaction(self, values):

        res = False
        transactionDateTime = datetime.now()

        if 'member_account_ids' in values:  # check if account types of member are passed for transaction, else no transaction
            memberAccount = values['member_account_ids']
            for acc in memberAccount:
                if isinstance(acc[2], dict) and 'tmp_transaction_amount' in acc[
                    2]:  # check if withdrawal amount is passed from ui
                    requestedAmount = acc[2]['tmp_transaction_amount']
                    account_id = acc[1]
                    if not ('tmp_transaction_date' in acc[2]):
                        transactionDateTime = datetime.now()
                    else:
                        transactionDateTime = acc[2]['tmp_transaction_date']
                    refNumber = ''
                    if 'tmp_ref_number' in values:
                        refNumber = values['tmp_ref_number']
                    if 'tmp_journal_id' in values:
                        journalID = values['tmp_journal_id']
                    else:
                        journalID = self.tmp_journal_id.id
                    if refNumber == '':
                        refNumber = self.member_id_number

                    serviceCharge = self.getWithdrawalServiceChargeAmount(account_id, requestedAmount)

                    if self.hasMemberAccountEnoughBalanceToWithdraw(account_id, serviceCharge + requestedAmount):

                        res = self.saveTransaction('withdrawal', transactionDateTime, account_id, requestedAmount,
                                                   values)
                        if res and (
                                serviceCharge > 0):  # If service charge is set and calculated deduct and save amount from account
                            values['tmp_transaction_note'] = "Service Charge"
                            res = self.saveTransaction('withdrawal', transactionDateTime, account_id, serviceCharge,
                                                       values)

                        if res:  # If Withdrawal is saved successfully, create accounting journal entry

                            res = self.createAccountingEntryForWithdrawal(requestedAmount, serviceCharge, journalID,
                                                                          account_id,
                                                                          transactionDateTime,
                                                                          refNumber)

        return res

    def saveTransaction(self, tran_type, date_time, account_id, amount, values):
        # This method should be moved to account object
        res = False
        assert amount > 0, "Invalid transaction Amount %s, Amount cant be less than zero'." % (str(amount))
        tranNote = refNumber = checkNumber = ""
        bankAccount = 0  # Todo: Map to existing bank account starting from journal id, if it is mandatory
        paymentMethod = 'cash'  # check, #transfer

        if 'tmp_ref_number' in values:
            refNumber = values['tmp_ref_number']
        if 'tmp_check_number' in values:
            checkNumber = values['tmp_check_number']
            paymentMethod = 'check'
        if 'tmp_payment_method' in values:
            paymentMethod = values['tmp_payment_method']
        if 'tmp_transaction_note' in values:
            tranNote = values['tmp_transaction_note']

        account = self.env['smif.member_account'].search([('id', '=', account_id)])
        if (tran_type == 'withdrawal'):
            assert account.current_balance >= amount, "Insufficient Balance to withdraw"
            account.current_balance -= amount
        if tran_type == 'deposit':
            account.current_balance += amount

        tran = {'member_ids': self.id,
                'transaction_amount': amount,
                'transaction_balance': account.current_balance,
                'transaction_type': tran_type,
                'transaction_date': date_time,
                'account_ids': account_id,
                'ref_number': refNumber,
                'check_number': checkNumber,
                'transaction_note': tranNote,
                'bank_id': bankAccount,
                'payment_method': paymentMethod}
        res = self.env['smif.transaction'].create(tran)

        if res != False:  # if transaction saved successful update account balance
            if (self.env['smif.member_account'].write(
                    account) == False):  # If Transaction unable to update account balance successfully
                res = False  # Return false to not take  any other accounting actions, else return transaction number
        return res

    def open_member_deposit(self):
        return {
            'name': 'Member Deposit',
            'res_model': 'smif.member',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_deposit_tran_view_form',
                        'default_tmp_transaction_type': 'deposit'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_deposit_tran_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_deposit_tran_view_form').id,
            'target': 'new'
        }

    def open_member_withdrawal(self):
        return {
            'name': 'Member Withdrawal',
            'res_model': 'smif.member',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_withdrawal_tran_view_form',
                        'default_tmp_transaction_type': 'withdrawal'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_withdrawal_tran_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_withdrawal_tran_view_form').id,
            'target': 'new',

        }

    def open_member_transfer(self):
        return {
            'name': 'Account Transfer',
            'res_model': 'smif.member',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_transfer_tran_view_form',
                        'default_tmp_transaction_type': 'transfer'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_transfer_tran_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_transfer_tran_view_form').id,
            'target': 'new'
        }

    def loan_view(self):
        return {
            'name': 'Member Loan View',
            'res_model': 'smif.member',  # ,
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_member_loan_view_form'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_member_loan_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_member_loan_view_form').id,
            'target': 'new',
            'flags': {'mode': 'readonly'}
        }

    def member_deactivation(self):
        self.calculate_member_deactivation(datetime.now().date())
        return {
            'name': 'Member Deactivation',
            'res_model': 'smif.member',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {'form_view_ref': 'smif.smif_member_deactivation_form',
                        'default_tmp_transaction_type': 'deactivation'},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_member_deactivation_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_member_deactivation_form').id,
            'target': 'new'
        }

    def get_id_auto_generate_setting(self):
        id_setting = self.env['ir.config_parameter'].sudo().get_param('smif.auto_generate_member_id') or False
        self.is_member_id_auto_generated = id_setting
        return id_setting

    def get_member_accounts(self):
        for acc in self.member_account_ids:
            self.tmp_transfer_to_account_id.__add__(acc)

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
