from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from datetime import datetime


class SmifAccountType(models.Model):
    _name = 'smif.account_type'
    _rec_name = 'account_name'
    _description = 'Account Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    account_name = fields.Char(string="Account Name", required=True, )
    interest_rate = fields.Float(string="Interest Rate", required=True, tracking=True, digits=(12, 2))
    is_time_blocked_account = fields.Boolean(string="Is Blocked Account", default=False,
                                             help="If Check Member Can't withdraw from account before minimum set months. "
                                                  "Else withdrawal is allowed at any time.")
    is_compulsory_account = fields.Boolean(string="Is Compulsory Account", default=False,
                                           help="If check all members must have this account type.")
    minimum_months_deposit = fields.Integer(string="Minimum Months Blocked",
                                            default=0, tracking=True,
                                            help="Number of minimum months withdrawal prohibited, Zero (0) for no limit.")
    minimum_saving_amount = fields.Float(string="Minimum Saving Amount", default=0, required=False, tracking=True,
                                         help="Minimum required saving amount per transaction.", digits=(12, 2))

    maximum_withdrawal_allowed = fields.Float(string="Allowed Maximum Withdrawal", default=0, required=True,
                                              tracking=True,
                                              help="Maximum allowed withdrawal amount at a time for this account, Zero (0) for no limit.",
                                              digits=(12, 2))
    minimum_saving_in = fields.Selection(string="Minimum Saving In", config_parameter="smif.minimum_saving_in",
                                         selection=[('amount', 'Amount'), ('percentage', 'Salary Percentage'),
                                                    ('NA', 'Not Required')], default='NA', required=True,
                                         help=" Not Required: Minimum Saving is not mandatory\n"
                                              " Amount: Minimum Saving in Birr.\n"
                                              " Salary Percentage: Minimum Saving based on percentage, is applicalbe for Employee "
                                              "Based Saving")
    withdrawal_service_charge = fields.Selection(string="Withdrawal Service Charge", tracking=True,
                                                 selection=[('amount', 'Amount'), ('percentage', 'Percentage'),
                                                            ('NA', 'No Service Charge')], default='NA', required=True,
                                                 help=" No Service Charge: There will be no service charge.\n"
                                                      " Amount: Add fixed amount of service charge on members withdrawal from account.\n"
                                                      " Percentage: Calculate service charge based on set pecentage from withdrawal amount.")

    service_charge = fields.Float(string="Service Charge", default=0, required=True,
                                  tracking=True,
                                  help="Withdrawal Service Charge", digits=(12, 2))
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
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", tracking=True,
        Help="Will be used only if service charge is enabled for the account and calculated when withdrawing from "
             "account")


class SmifMemberAccount(models.Model):
    _name = 'smif.member_account'
    _rec_name = 'account_disc'
    _description = 'Member Account'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    member_ids = fields.Many2one('smif.member',  # ,
                                 string='Member', index=True)
    account_type = fields.Many2one('smif.account_type', string='Account Type', index=True, tracking=True)
    # account_number = fields.Char(string='Account Number', required=True, tracking=True)
    account_number = fields.Char(string='Account Number', required=False, copy=False, readonly=True, index=True,
                                 default='[Auto]')
    account_created_date = fields.Date(string='Created Date', default=datetime.now())
    initial_deposit = fields.Monetary(string="Initial Deposit", required=True, tracking=True, )
    transaction_ids = fields.One2many('smif.transaction', 'account_ids', string='Transactions', index=True)
    type_name = fields.Char(related='account_type.account_name')

    current_balance = fields.Monetary(string="Balance", tracking=True)

    tmp_transaction_amount = fields.Monetary(string="Amount", store=False, )
    tmp_transaction_date = fields.Datetime(string="Date Time", store=False, default=datetime.now())

    account_disc = fields.Char(string='Combination', compute='_compute_account_disc')

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    is_accounting_set = fields.Boolean('Is Accounting Set', default=False)
    is_active = fields.Boolean('Is Active', default=True)
    last_int_date = fields.Date(string="Date Time", store=True, default=datetime.now())
    # Transfer from account to account

    tmp_transfer_from_account = fields.Boolean('From Account', default=False, store=False)
    tmp_transfer_to_account = fields.Boolean('To Account', default=False, store=False)

    # @api.depends('tmp_transfer_from_account')
    # def _tmp_transfer(self):
    #     for rec in self:
    #         if rec.tmp_transfer_from_account==True:
    #             rec.tmp_transfer_to_account=False
    #         else:
    #             rec.tmp_transaction_amount=0

    @api.depends('account_number', 'type_name')
    def _compute_account_disc(self):
        for val in self:
            val.account_disc = str(val.type_name) + ' (' + val.account_number + ')'

    parent_member_id = fields.Integer(string='Member ID', compute='_get_parent_member_id')

    def _get_parent_member_id(self):
        for val in self:
            val.parent_member_id = val.member_ids.id

    def create(self, vals):
        for val in vals:
            id_Val = str(self.env['ir.sequence'].next_by_code('member_account_number_sqc'))
            val['account_number'] = id_Val
            res = super(SmifMemberAccount, self).create(val)
        return res

    def open_account_history(self):
        return {
            'name': 'Transaction History',
            'res_model': 'smif.member_account',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_transaction_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_transaction_view_form').id,
            'target': 'new',
            'flags': {'mode': 'readonly'}
        }

    def get_account_payment_amount(self):
        acc_type = self.account_type
        amount = 0
        if acc_type.minimum_saving_in == 'percentage':
            amount = acc_type.minimum_saving_amount * self.member_ids.salary / 100
        elif acc_type.minimum_saving_in == 'amount':
            amount = acc_type.minimum_saving_amount

        return amount

    def get_total_interest_invalid_deposit(self, min_valid_depo_date):
        res = 0
        depo_total = 0
        with_total = 0
        # Todo: Load all deposit greater than min_valid_depo_date, and retur total sum
        acc_tran = self.env['smif.transaction'].search(
            [('account_ids', '=', self.id), ('transaction_date', '>', min_valid_depo_date)])
        for tran in acc_tran:
            if tran.transaction_type == 'deposit':
                depo_total += tran.transaction_amount
            # elif tran.transaction_type == 'withdrawal':
            #     with_total += tran.transaction_amount

        return depo_total  # abs(depo_total - with_total)

    def calculate_interest_for_accounts_yearly_monthly_daily(self, accounts, account_type):

        res = False
        int_date = datetime.now().date()
        distance_from_prev_int_date = 0

        int_rate = account_type.interest_rate / 100
        minim_duration_for_int = int(
            self.env['ir.config_parameter'].sudo().get_param('smif.minimum_deposit_duration_for_int'))

        saving_interest_period = self.env['ir.config_parameter'].sudo().get_param('smif.saving_interest_period')
        if not saving_interest_period:
            saving_interest_period = 'monthly'  # if not set default to monthly

        if saving_interest_period == 'yearly':  # If Interest is calculated yearly
            distance_from_prev_int_date = 360
            max_valid_date = int_date - relativedelta(months=minim_duration_for_int)
        elif saving_interest_period == 'monthly':  # If Interest is calculated monthly
            int_rate = int_rate / 12
            distance_from_prev_int_date = 30
            max_valid_date = int_date - relativedelta(days=minim_duration_for_int)
        elif saving_interest_period == 'daily':
            int_rate = int_rate / 360
            distance_from_prev_int_date = 1
            max_valid_date = int_date - relativedelta(days=minim_duration_for_int)

        chart_of_acc_int = int(self.env['ir.config_parameter'].sudo().get_param('smif.saving_interest_account'))
        chart_of_acc_type = account_type.default_account_id.id

        total_interest_amount = 0
        for acc in accounts:

            diff = int_date - acc.last_int_date
            if diff.days >= distance_from_prev_int_date:  # Make sure distance from previus int. is valid
                balance = acc.current_balance
                balance = balance - acc.get_total_interest_invalid_deposit(max_valid_date)
                int_amount = round(balance * int_rate, 2)
                if int_amount > 0:
                    acc.last_int_date = int_date
                    res = acc.saveAccountTransaction('deposit', int_date, int_amount, '', '', 'Interest Deposit')
                    if res:
                        total_interest_amount += int_amount

        if total_interest_amount > 0:
            debit_side_int = acc.prepare_acc_side(total_interest_amount, chart_of_acc_int, 'debit',
                                                  "Interest")  # Debit Saving Interest
            credit_side_acc_type = acc.prepare_acc_side(total_interest_amount, chart_of_acc_type, 'credit',
                                                        'Interest')  # Credit account type
            lines = [(0, 0, debit_side_int), (0, 0, credit_side_acc_type)]

            journalID = 0
            journal = acc.env['account.journal'].search([])
            for jor in journal:
                if 'Miscellaneous' in jor.name:
                    journalID = jor.id
                    break
            assert journalID > 0, 'Cant Find Miscellaneous Journal, Please Configure it.'
            res = acc.createJournalEntry(lines, journalID, int_date, '')

        return res

    def deposit_interest_to_account(self, interest):
        int_amount = interest.interest_amount
        # int_date = interest.interest_date
        res = False
        if int_amount > 0:
            # self.last_int_date = int_date
            res = self.saveAccountTransaction('deposit', datetime.now(), int_amount, '', '', 'Interest Deposit')
        return res

    def post_interest_to_accounting(self, int_date, int_amount, chart_of_acc):
        chart_of_acc_int = int(self.env['ir.config_parameter'].sudo().get_param('smif.saving_interest_account'))
        # chart_of_acc_type = self.account_type.default_account_id.id
        # int_date = interest.interest_date
        # int_amount = interest.interest_amount
        res = False
        if int_amount > 0:
            debit_side_int = self.prepare_acc_side(int_amount, chart_of_acc_int, 'debit',
                                                   'Interest')  # Debit Saving Interest
            credit_side_acc_type = self.prepare_acc_side(int_amount, chart_of_acc, 'credit',
                                                         'Interest')  # Credit account type
            lines = [(0, 0, debit_side_int), (0, 0, credit_side_acc_type)]

            journalID = 0
            journal = self.env['account.journal'].search([])
            for jor in journal:
                if 'Miscellaneous' in jor.name:
                    journalID = jor.id
                    break
            assert journalID > 0, 'Cant Find Miscellaneous Journal, Please Configure it.'
            res = self.createJournalEntry(lines, journalID, int_date, '')
        return res

    def calculate_interest_for_account(self, int_date):
        res = False

        distance_from_prev_int_date = 0

        int_rate = self.account_type.interest_rate / 100
        minim_duration_for_int = int(
            self.env['ir.config_parameter'].sudo().get_param('smif.minimum_deposit_duration_for_int'))

        saving_interest_period = self.env['ir.config_parameter'].sudo().get_param('smif.saving_interest_period')

        if saving_interest_period == 'yearly':  # If Interest is calculated yearly
            distance_from_prev_int_date = 360
            max_valid_date = int_date - relativedelta(months=minim_duration_for_int)
        elif saving_interest_period == 'monthly':  # If Interest is calculated monthly
            int_rate = int_rate / 12
            distance_from_prev_int_date = 30
            max_valid_date = int_date - relativedelta(days=minim_duration_for_int)
        elif saving_interest_period == 'daily':
            int_rate = int_rate / 360
            distance_from_prev_int_date = 1
            max_valid_date = int_date - relativedelta(days=minim_duration_for_int)

        int_amount = 0

        diff = int_date - self.last_int_date

        if diff.days >= distance_from_prev_int_date:  # Make sure distance from previous int. is valid
            balance = self.current_balance
            balance = balance - self.get_total_interest_invalid_deposit(max_valid_date)
            int_amount = round(balance * int_rate, 2)

            self.last_int_date = datetime.now()
        # interest.int_amount = int_amount

        return int_amount

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

    def start_saving_interest_calculation(self):
        account_types = self.env['smif.account_type'].search([])
        # type_detail = self.env['smif.account_type'].browse(account_types)

        for type in account_types:
            accounts = self.env['smif.member_account'].search(
                [('is_active', '=', True), ('account_type', '=', type.id), ('current_balance', '>', 0)])
            if len(accounts) > 0:
                self.calculate_interest_for_accounts(accounts, type)

    def saveAccountTransaction(self, tran_type, date_time, amount, ref_number, check_number, tran_note):
        res = False
        assert amount > 0, "Invalid transaction Amount %s, Amount cant be less than zero'." % (str(amount))
        assert self.is_active, 'Member Account Not Active, Unable to transaction'

        bank_account = 0  # Todo: Map to existing bank account starting from journal id, if it is mandatory
        payment_method = 'cash'
        if check_number != '':
            payment_method = 'check'

        if tran_type == 'withdrawal':
            assert self.current_balance >= amount, "Insufficient Balance to withdraw"
            self.current_balance -= amount
        if tran_type == 'deposit':
            self.current_balance += amount
        tran = {'member_ids': self.member_ids.id,
                'transaction_amount': amount,
                'transaction_balance': self.current_balance,
                'transaction_type': tran_type,
                'transaction_date': date_time,
                'account_ids': self.id,
                'ref_number': ref_number,
                'check_number': check_number,
                'transaction_note': tran_note,
                'bank_id': bank_account,
                'payment_method': payment_method}
        res = self.env['smif.transaction'].create(tran)

        if res:  # if transaction saved successful update account balance
            if not self.env['smif.member_account'].write(
                    self):  # If Transaction unable to update account balance successfully
                res = False  # Return false to not take  any other accounting actions, else return transaction number
        return res


def show_message(msg_title, message_to_display, msg_type):
    notification = {
        'type': "ir.actions.client",
        'tag': "display_notification",
        'params': {
            'title': msg_title,
            'message': message_to_display,
            'type': msg_type,
            'sticky': True,
        },
    }
    return notification


class SmifInterest(models.Model):  # Parent
    _name = 'smif.interest'
    _description = 'Interest'
    _rec_name = 'generation_date'
    status = fields.Selection(string="Status",
                              selection=[('open', 'Open'), ('deposited', 'Deposited'),
                                         ('posted', 'Posted')],
                              required=True, default='open')
    # month = fields.Selection(string="Month",
    #                           selection=[('1','January'),('2','February'),('3','March'),('4','April'),('5','May'),('6','June'),('7','July'),('8','August'),('9','September'),('10','October'),('11','November'),('12','December')],
    #                           required=True, default='1')
    generation_date = fields.Date(string='Generation Date', default=datetime.now())
    from_date = fields.Date(string='From Date', default=datetime.now())
    upto_date = fields.Date(string='Upto Date', default=datetime.now())

    account_interests = fields.One2many('smif.account_interest', 'interest_id', string='Accounts Interest')
    generated_by = fields.Selection(string="Generated By",
                                    selection=[('user', 'User'), ('system', 'System')],
                                    required=True, default='user')

    def calculate_interest(self):
        params = []

        params.append(('is_active', '=', True))
        active_accounts = self.env['smif.member_account'].search(params)
        int_date = self.from_date
        for acc in active_accounts:
            rate = acc.account_type.interest_rate
            amnt = acc.calculate_interest_for_account(int_date)
            if amnt > 0:
                self.create_acc_interest(acc, int_date, amnt, rate)

        return ""

    def post_deposited(self):  # To Accounting
        ready_for_int = {}
        count = 0
        int_date = datetime.now()
        for int in self.account_interests:
            int_date = int.interest_date
            if int.status == 'deposited':
                acc_id = int.account_id.account_type.default_account_id.id
                int.status = 'posted'
                count = count + 1
                if ready_for_int.__contains__(acc_id):
                    ready_for_int[acc_id] = ready_for_int[acc_id] + int.interest_amount
                else:
                    ready_for_int[acc_id] = int.interest_amount

        all_count = self.account_interests.__len__()

        if ready_for_int.__len__() > 0:
            for _key in ready_for_int.keys():  # _key is chart of account for account type
                res = int.account_id.post_interest_to_accounting(int_date, ready_for_int[_key], _key)
            msg = show_message('Posted To Account',
                               str(count) + ' of ' + str(all_count) + ' Account Interest Transaction Posted', 'success')
        else:
            msg = show_message('Not Posted',
                               str(count) + ' of ' + str(all_count) + ' Account Interest Transaction not posted',
                               'danger')
        return msg

    def deposit_to_account(self):  # Deposit
        count = 0
        all_count = 0
        for int in self.account_interests:
            if int.status == 'open':
                res = int.account_id.deposit_interest_to_account(int)
                if res:
                    count = count + 1
                    int.status = 'deposited'
            all_count = all_count + 1

        if count > 0:
            msg = show_message('Deposited To Account',
                               str(count) + ' of ' + str(all_count) + ' Account Interest Deposited to Account',
                               'success')
        else:
            msg = show_message('Not Deposited',
                               str(count) + ' of ' + str(all_count) + ' Account Interest No Deposited to Account',
                               'danger')
        return msg

    def get_account_daily_balance(self, acc, from_date, to_date):
        params = []

        params.append(('is_active', '=', True))
        active_accounts = self.env['smif.member_account'].search(params)

    def create_acc_interest(self, acc, int_date, amount, rate):
        acc_inter = self.env['smif.account_interest']
        values = {
            'account_id': acc.id,
            'status': 'open',
            'interest_date': int_date,
            'interest_amount': amount,
            'interest_rate': rate,
            'interest_id': self.id
        }
        super(SmifAccountInterest, acc_inter).create(values)


class SmifAccountInterest(models.Model):  # Child
    _name = 'smif.account_interest'
    _description = 'Account Interest'

    account_id = fields.Many2one('smif.member_account', string='Account')

    status = fields.Selection(string="Status",
                              selection=[('open', 'Open'), ('deposited', 'Deposited'),
                                         ('posted', 'Posted')],
                              required=True, default='open')
    interest_date = fields.Date(string='Interest Date', default=datetime.now())
    interest_rate = fields.Float(string='Rate', required=True, )
    interest_amount = fields.Float(string='Interest', required=True, )
    interest_id = fields.Many2one('smif.interest', string='Interest')
    member_name = fields.Char(string='Member Name', compute='_get_member_name')

    @api.depends('account_id')
    def _get_member_name(self):
        for rec in self:
            if rec.account_id:
                rec.member_name = rec.account_id.member_ids.fullName
