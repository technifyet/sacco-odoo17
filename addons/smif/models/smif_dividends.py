from datetime import datetime

from odoo import models, fields, api


class SmifDividendBulkPayment(models.Model):
    _name = 'smif.dividends_bulk_payment'
    _description = 'Bulk Payment Model for Dividends'
    # The following are used only for bulk devidend payment, and are temporary

    tmp_payment_mode = fields.Selection(string="Mode of Settlement",
                                        selection=[('cash', 'Cash Payment'), ('loan', 'Loan Payment'),
                                                   ('account', 'Account Transfer'), ('share', 'Share Purchase'), ],
                                        required=True, default='cash')
    tmp_account_type_id = fields.Many2one('smif.account_type', string='Account',
                                          select=True,
                                          )
    tmp_dividend = fields.Many2one('smif.dividends', string='Dividend',
                                   select=True,
                                   )
    # tmp_loan_type_id = fields.Many2one('smif.loan_type', string='Loan', )
    tmp_payment_journal_id = fields.Many2one('account.journal', string='Paid On',
                                             check_company=True, required=False)
    # tmp_company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    tmp_payment_date = fields.Date(string='Payment Date', default=datetime.now())
    tmp_payment_ref_number = fields.Char('Reference Number', )
    tmp_check_number = fields.Char('Check Number', )

    tmp_share = fields.Many2one('smif.shares', string='Share', )
    tmp_purchased_quantity = fields.Integer(string="Quantity", )

    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    def save_bulk_settlement(self):
        return ""


class SmifDividends(models.Model):
    _name = 'smif.dividends'
    _description = 'Calculated Share Dividends'

    _rec_name = 'dividend_generation_date'
    all_selected = fields.Integer(string="Select/Unselect All", store=True, default=0)

    from_date = fields.Date(string="From Date", required=True, )
    upto_date = fields.Date(string="Up to Date", required=True, )
    net_income = fields.Float(string='Net Income', )

    members_dividend_amount = fields.Float(string='Member Dividend', readonly=False, store=True,
                                           compute='compute_members_dividend_amount')
    company_dividend_amount = fields.Float(string='Company Dividend', help="Retained Earning", readonly=False,
                                           store=True, compute='compute_company_dividend_amount')

    all_member_total_savings = fields.Float(string='Total Savings', )
    shares_total_available = fields.Float(string='Total Shares Sold', )

    dividend_generation_date = fields.Date(string="Generation Date", readonly=True, default=datetime.now())

    members_dividend = fields.One2many('smif.member_dividend', 'dividend_ids', string='Member Dividend')
    status = fields.Selection(string="Status",
                              selection=[('created', 'Created'), ('generated', 'Generated'), ('paying', 'Paying'),
                                         ('paid', 'Paid'), ('posted', 'Posted'), ],
                              required=True, default='created')

    @api.onchange('net_income')
    def _compute_sum(self):
        memb_div_per = float(self.env['ir.config_parameter'].sudo().get_param('smif.member_dividend_percentage'))
        comply_div_per = float(self.env['ir.config_parameter'].sudo().get_param('smif.retained_earning'))

        self.members_dividend_amount = self.net_income * memb_div_per / 100
        self.company_dividend_amount = self.net_income * comply_div_per / 100

    @api.depends('net_income')
    def compute_members_dividend_amount(self):
        memb_div_per = float(self.env['ir.config_parameter'].sudo().get_param('smif.member_dividend_percentage'))
        self.members_dividend_amount = self.net_income * memb_div_per / 100
        return self.members_dividend_amount

    @api.depends('net_income')
    def compute_company_dividend_amount(self):
        comply_div_per = float(self.env['ir.config_parameter'].sudo().get_param('smif.retained_earning'))
        self.company_dividend_amount = self.net_income * comply_div_per / 100
        return self.company_dividend_amount

    def calculate_totals(self, members):
        savings = 0
        shares = 0
        for memb in members:
            savings = savings + self.get_member_toatl_saving(memb)
            # shares = shares + self.get_member_total_share(memb)

        self.all_member_total_savings = savings
        self.shares_total_available = self.get_total_avlbl_share()

    def select_all(self):
        if self.all_selected == 0:
            self.all_selected = 1
            for memb in self.members_dividend:
                if memb.status != 'paid':
                    memb.select_row()
        else:
            self.all_selected = 0
            for memb in self.members_dividend:
                memb.unselect_row()

    def view_bulk_payment(self):
        selected_count = 0
        for rec in self.members_dividend:
            if rec.is_selected:
                selected_count = selected_count + 1

        if selected_count > 0:
            self.all_selected = 2

            mem_dvd = self.members_dividend[0]

            # This loop is only to get the first unpaid payment object to use it as template
            for rec in self.members_dividend:
                if rec.status == 'payable' or rec.status == 'partial':
                    mem_dvd = rec
                    break

            mem_dvd.is_bulk_settlement_mode = True
            return {
                'name': 'Bulk Dividend Settlement',
                'res_model': 'smif.member_dividend',
                'type': 'ir.actions.act_window',
                'res_id': mem_dvd.id,
                'context': {},
                'view_mode': 'form',
                'views': [(self.env.ref('smif.smif_dividend_settlement_view_form').id, 'form')],
                'view_id': self.env.ref('smif.smif_dividend_settlement_view_form').id,
                'target': 'new',

            }
        else:
            return show_error_message("Member Not Selected",
                                      "Please Select at least one or more member to perform bulk payment")
    #
    # def check_and_update_if_paid(self):
    #     paid_count = 0
    #     posted_count = 0
    #     for rec in self.members_dividend:
    #         if rec.status == 'paid':
    #             paid_count = paid_count + 1
    #         elif rec.status == 'posted':
    #             paid_count = paid_count + 1
    #             posted_count = posted_count + 1
    #
    #     if (posted_count > 0) and (self.members_dividend.__len__() == posted_count):
    #         values = {
    #             'status': 'posted',
    #         }
    #         super(SmifDividends, self).update(values)
    #     elif (paid_count > 0) and (self.members_dividend.__len__() == paid_count):
    #         values = {
    #             'status': 'paid',
    #         }
    #         super(SmifDividends, self).update(values)



    def generate_members_dividend(self):

        params = []

        params.append(('active', '=', True))
        members = self.env['smif.member'].search(params)

        self.calculate_totals(members)

        calc_dividend_by = self.env['ir.config_parameter'].sudo().get_param('smif.calc_dividend_by')

        if calc_dividend_by == 'saving':
            self.generate_by_saving_ownership(members)
        elif calc_dividend_by == 'share':
            self.generate_by_share_ownership(members)
        elif calc_dividend_by == 'both':

            saving_percentage = float(
                self.env['ir.config_parameter'].sudo().get_param('smif.member_dividend_saving_percentage'))
            share_percentage = float(
                self.env['ir.config_parameter'].sudo().get_param('smif.member_dividend_share_percentage'))
            self.generate_by_share_and_saving_ownership(members, saving_percentage, share_percentage)
        for rec in self:
            rec.status = 'generated'

        self.post_dividend_to_accounting()

    def post_dividend_to_accounting(self):
        res = False
        if self.members_dividend_amount > 0:
            dvd_payable = int(self.env['ir.config_parameter'].sudo().get_param('smif.dvd_account_payable'))
            retained_ear_acc = int(self.env['ir.config_parameter'].sudo().get_param('smif.retained_earning_account'))
            credit_side_dvd_payable = self.prepare_acc_side(self.members_dividend_amount, dvd_payable, 'credit',
                                                            "Members Dividend Payable")
            cred_reained_ear = self.prepare_acc_side(self.company_dividend_amount, retained_ear_acc, 'credit',
                                                     "Company Retained Earning")

            lines = [(0, 0, cred_reained_ear), (0, 0, credit_side_dvd_payable)]

            journalID = 0
            journal = self.env['account.journal'].search([])
            for jor in journal:
                if 'Miscellaneous' in jor.name:
                    journalID = jor.id
                    break
            assert journalID > 0, 'Cant Find Miscellaneous Journal, Please Configure it.'
            res = self.createJournalEntry(lines, journalID, datetime.now(), '')

        return res

    def generate_by_saving_ownership(self, members):
        for memb in members:
            memb_saving_dvd, saving_balance = self.get_member_divd_from_saving(memb)
            self.create_memb_dividend_entry(memb, memb_saving_dvd, 0, saving_balance, 0, memb_saving_dvd)
        return

    def generate_by_share_ownership(self, members):
        for memb in members:
            memb_share_dvd, shares = self.get_member_divd_from_share(memb)
            self.create_memb_dividend_entry(memb, 0, memb_share_dvd, 0, shares, memb_share_dvd)
        return

    def generate_by_share_and_saving_ownership(self, members, saving_percentage, share_percentage):
        for memb in members:
            memb_saving_dvd, saving_bal = self.get_member_divd_from_saving(memb)
            memb_share_dvd, share_quant = self.get_member_divd_from_share(memb)

            memb_saving_dvd = (memb_saving_dvd * saving_percentage / 100)
            memb_share_dvd = (memb_share_dvd * share_percentage / 100)

            total = memb_saving_dvd + memb_share_dvd
            self.create_memb_dividend_entry(memb, memb_saving_dvd, memb_share_dvd, saving_bal, share_quant, total)

        return

    def get_member_toatl_saving(self, member):
        amount = 0
        for acct in member.member_account_ids:
            if acct.is_active and acct.account_type.is_compulsory_account:
                amount = amount + acct.current_balance

        return amount

    # def get_member_total_share(self, member):
    #     amount = 0
    #     for share in member.shares_purchased_ids:
    #         if share.is_active:
    #             amount = amount + share.total_amount
    #
    #     return amount
    #

    def get_total_avlbl_share(self, ):
        total_shares_avl = 0
        all_shares = self.env['smif.shares'].search([])
        for sh in all_shares:
            total_shares_avl = total_shares_avl + sh.totalInitialShareQuantity

        return total_shares_avl

    def get_member_divd_from_saving(self, member):
        amount = 0
        balance = 0
        for acct in member.member_account_ids:
            if acct.is_active and acct.account_type.is_compulsory_account:
                balance = balance + acct.current_balance

        if self.all_member_total_savings > 0:
            memb_percentage = balance * 100 / self.all_member_total_savings

            amount = self.members_dividend_amount * memb_percentage / 100

        return amount, balance

    def get_member_divd_from_share(self, member):
        shares = 0
        amount = 0
        for share in member.shares_purchased_ids:
            if share.is_active:
                shares = shares + share.purchased_quantity

        if self.shares_total_available > 0:
            memb_percentage = shares * 100 / self.shares_total_available

            amount = self.members_dividend_amount * memb_percentage / 100

        return amount, shares

    def create_memb_dividend_entry(self, member, saving_divd, share_divd, memb_saving, memb_share, total_dividend):
        mem_dividend = self.env['smif.member_dividend']
        values = {
            'member_id': member.id,
            'dividend_ids': self.id,
            'saving_dividend': saving_divd,
            'total_member_saving': memb_saving,
            'total_member_shares': memb_share,
            'share_dividend': share_divd,
            'total_member_dividend': total_dividend
        }
        super(SmifMemberDividend, mem_dividend).create(values)

    def handle_bulk_posting(self):
        total_paid = 0
        posted_items = []
        prv_posted_count = 0
        res=False
        for mem_pay in self.members_dividend:
            if mem_pay.status == 'paid':
                total_paid = total_paid + mem_pay.total_member_dividend
                posted_items.append(mem_pay)
            elif mem_pay.status == 'posted':
                prv_posted_count = prv_posted_count + 1

        if total_paid > 0:
            dvd_acc = int(self.env['ir.config_parameter'].sudo().get_param('smif.dvd_account_paid'))
            debit_side_dvd = self.prepare_acc_side(total_paid, dvd_acc, 'debit', "Member Dividend Paid")
            lines = [(0, 0, debit_side_dvd)]

            journalID = 0
            journal = self.env['account.journal'].search([])
            for jor in journal:
                if 'Miscellaneous' in jor.name:
                    journalID = jor.id
                    break
            assert journalID > 0, 'Cant Find Miscellaneous Journal, Please Configure it.'
            res = self.createJournalEntry(lines, journalID, datetime.now(), '')

            if res:
                for itm in posted_items:
                    itm.status = 'posted'


                if (prv_posted_count + posted_items.__len__()) == self.members_dividend.__len__():  # all are posted

                    val={'status':'posted'}
                    super(SmifDividends, self).write(val)
                    res = show_message('All Posted','All Transactions are posted now','success')
                else:
                    res = show_message('Posted', str(posted_items.__len__())+' paid transactions are posted now', 'success')
        elif prv_posted_count == self.members_dividend.__len__():
            res = show_error_message('Nothing to Post', 'All Transactions are posted already')
        else:
            res=show_error_message('Nothing to Post', 'Pleas make payment first. Paid Transactions not found.')

        return res

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


class SmifMemberDividend(models.Model):  # Child
    _name = 'smif.member_dividend'
    _description = 'Each Members Dividend'
    is_bulk_settlement_mode = fields.Boolean(string='Is Bulk')
    is_selected = fields.Boolean(string='Select')
    member_id = fields.Many2one('smif.member', string='Member', index=True)
    saving_dividend = fields.Float(string='Saving Dividend', )
    share_dividend = fields.Float(string='Share Dividend', )

    total_member_saving = fields.Float(string='Member Savings', )
    total_member_shares = fields.Float(string='Member Shares', )

    total_member_dividend = fields.Float(string='Total Dividend', )
    remaining_amount = fields.Float(string='Remaining Payment', compute='compute_remaining_payment')

    dividend_ids = fields.Many2one('smif.dividends', string='Dividend', index=True)
    settlements_ids = fields.One2many('smif.dividend_settlement', 'memb_divid', string='Member Dividend')
    status = fields.Selection(string="Status",
                              selection=[('payable', 'Payable'), ('partial', 'Partial'), ('paid', 'Paid'),
                                         ('posted', 'Posted')],
                              required=True, default='payable')

    tmp_payment_mode = fields.Selection(string="Mode of Settlement",
                                        selection=[('cash', 'Cash Payment'), ('loan', 'Loan Payment'),
                                                   ('account', 'Account Transfer'), ('share', 'Share Purchase'), ],
                                        required=True, default='cash')
    tmp_account_id = fields.Many2one('smif.member_account', string='Member Account',
                                     domain="[('member_ids.id', '=', tmp_mem_id)]",
                                     select=True,
                                     )
    tmp_loan_id = fields.Many2one('smif.loan_request', string='Member Loan',
                                  domain="[('member_id.id', '=', tmp_mem_id)]")
    tmp_payment_journal_id = fields.Many2one('account.journal', string='Paid On',
                                             check_company=True, required=False)
    # tmp_company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    tmp_payment_date = fields.Date(string='Payment Date', default=datetime.now())
    tmp_payment_ref_number = fields.Char('Reference Number', )
    tmp_check_number = fields.Char('Check Number', )

    tmp_share = fields.Many2one('smif.shares', string='Share', )
    tmp_purchased_quantity = fields.Integer(string="Quantity", )

    tmp_amount = fields.Float(string='Amount', required=True, )
    tmp_mem_id = fields.Integer(string="Member ID", compute='on_member_change')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    tmp_account_type_id = fields.Many2one('smif.account_type', string='Account Type')
    tmp_loan_type_id = fields.Many2one('smif.loan_type', string='Loan Type')

    @api.onchange('tmp_purchased_quantity', 'tmp_share')
    def purchased_share_quantity_change(self):
        if self.tmp_payment_mode == 'share' and self.tmp_share:
            self.tmp_amount = self.tmp_purchased_quantity * self.tmp_share.unitPrice

    @api.depends('member_id')
    def on_member_change(self):
        for rec in self:
            rec.tmp_mem_id = rec.member_id.id
            # rec.tmp_amount = rec.remaining_amount

    def make_payment(self):
        self.tmp_amount = self.remaining_amount
        self.tmp_payment_mode = 'cash'
        self.is_bulk_settlement_mode = False
        return {
            'name': 'Member Dividend Settlement',
            'res_model': 'smif.member_dividend',
            'type': 'ir.actions.act_window',
            'res_id': self.id,
            'context': {},
            'view_mode': 'form',
            'views': [(self.env.ref('smif.smif_dividend_settlement_view_form').id, 'form')],
            'view_id': self.env.ref('smif.smif_dividend_settlement_view_form').id,
            'target': 'new',

        }

    def select_row(self):
        if self.status != 'paid':
            self.is_selected = True

    def unselect_row(self):
        self.is_selected = False
        self.is_bulk_settlement_mode = False

    @api.depends('total_member_dividend')
    def compute_remaining_payment(self):

        for rec in self:
            total_paid = 0
            total_dvd = rec.total_member_dividend
            for dvd in rec.settlements_ids:
                total_paid = total_paid + dvd.amount

            rec.remaining_amount = round(total_dvd - total_paid, 2)

            if rec.status != 'posted':
                if rec.remaining_amount <= 0:
                    rec.status = 'paid'
                elif total_paid == 0:
                    rec.status = 'payable'
                elif total_paid < total_dvd:
                    rec.status = 'partial'

    def save_payment_settlement(self):
        if self.is_bulk_settlement_mode:
            self.handle_bulk_payment()
            self.is_bulk_settlement_mode = False
        else:  # Is Not Bulk so make payment to current object
            if self.tmp_amount > self.remaining_amount:
                return show_error_message('Amount Validation Error', 'Amount Must not exceed Remaining Dividend.')
            elif self.tmp_amount <= 0:
                return show_error_message('Amount Validation Error',
                                          'Invalid Amount Value, Amount has to be greater than Zero')
            else:
                return self.create_payment_settlement(False)

    def handle_bulk_payment(self):
        py_type = self.tmp_payment_mode

        for mem_pay in self.dividend_ids.members_dividend:
            if mem_pay.is_selected:

                ok_to_save = False
                amnt = mem_pay.remaining_amount

                mem_pay.tmp_payment_mode = py_type

                if py_type == 'account':
                    mem_pay.tmp_loan_id = 0
                    mem_pay.tmp_payment_journal_id = 0
                    mem_pay.tmp_payment_ref_number = ''
                    member_acc = mem_pay.member_id.get_member_account_by_type(self.tmp_account_type_id)
                    if member_acc:
                        mem_pay.tmp_account_id = member_acc.id
                        ok_to_save = True

                elif py_type == 'loan':
                    mem_pay.tmp_account_id = 0
                    mem_pay.tmp_payment_journal_id = 0
                    mem_pay.tmp_payment_ref_number = ''

                    member_ln = mem_pay.member_id.get_member_loan_by_type(self.tmp_loan_type_id)
                    if member_ln:
                        ok_to_save = True
                        mem_pay.tmp_loan_id = member_ln.id

                        lon_total = member_ln.calculated_total_remaining_loan
                        if amnt > lon_total:
                            amnt = lon_total

                elif py_type == 'cash':
                    ok_to_save = True

                    mem_pay.tmp_account_id = 0
                    mem_pay.tmp_loan_id = 0

                    mem_pay.tmp_payment_journal_id = self.tmp_payment_journal_id
                    mem_pay.tmp_payment_ref_number = self.tmp_payment_ref_number

                elif py_type == 'share':
                    mem_pay.tmp_share = self.tmp_share
                    mem_pay.tmp_purchased_quantity = self.tmp_purchased_quantity
                    share_amnt = self.tmp_share.unitPrice * self.tmp_purchased_quantity

                    if amnt >= share_amnt:
                        amnt = share_amnt
                        ok_to_save = True

                if ok_to_save:
                    mem_pay.tmp_amount = amnt
                    mem_pay.tmp_payment_date = self.tmp_payment_date
                    res = mem_pay.create_payment_settlement(True)
                    if res:
                        mem_pay.is_selected = False
        return ""

    def create_payment_settlement(self, is_bulk):
        mem_settl = self.env['smif.dividend_settlement']
        for rec in self:
            acc_id = 0
            ln_id = 0
            jorn_id = 0
            share_id = 0
            share_quantity = 0
            payment_ref = ""
            chk = ""
            amnt = rec.tmp_amount

            if rec.tmp_payment_mode == 'account':
                acc_id = rec.tmp_account_id.id
                vl = {
                    'tmp_payment_method': 'transaction',
                    'tmp_transaction_note': 'Member Dividend',
                    'tmp_ref_number': rec.id
                }
                result = self.member_id.saveTransaction('deposit', rec.tmp_payment_date, acc_id, amnt, vl)
            elif rec.tmp_payment_mode == 'loan':
                ln_id = rec.tmp_loan_id.id
                selected_loan = rec.tmp_loan_id
                loan_remained = selected_loan.calculated_total_remaining_loan
                if loan_remained <= 0:
                    return show_error_message('Error', 'Loan has no more remaining payment, Cant transfer to this loan')
                elif amnt > loan_remained:
                    return show_error_message('Error',
                                              'Amount to transfer is bigger than Remaining Loan Amount (' + str(
                                                  loan_remained) + '). , Cant transfer to this loan')
                else:
                    loan_inst = selected_loan.getNextPayableInstallment()
                    if loan_inst:
                        vls = {
                            'payment_ref_number': rec.id,
                            'paid_date': rec.tmp_payment_date,
                            'tmp_loan_payment_amount': amnt,
                            'tmp_saving_amount': 0,
                            # This is to remove saving deposit with loan, remove this line to include saving with loan payment
                            'payment_journal_id': ''
                        }
                        loan_inst.saveInstallmentPayment(vls)
            elif rec.tmp_payment_mode == 'cash':
                jorn_id = rec.tmp_payment_journal_id.id
                payment_ref = rec.tmp_payment_ref_number
                chk = rec.tmp_check_number
            elif rec.tmp_payment_mode == 'share':
                if not rec.tmp_share:
                    return show_error_message('Share Not Selected', 'Please Select Share and Purchased share quantity')
                elif rec.tmp_purchased_quantity <= 0:
                    return show_error_message('Validation Error', 'Share Quantity must be 1 or more', )
                elif amnt < (rec.tmp_share.unitPrice * rec.tmp_purchased_quantity):
                    return show_error_message('Validation Error',
                                              'Not Enough Amount to purchase selected quantity of share')
                elif rec.tmp_purchased_quantity > rec.tmp_share.remainingQuantity:
                    return show_error_message('No Enough Share',
                                              'Share quantity to purchase is less than availble amount.')

                share_id = rec.tmp_share.id
                share_quantity = rec.tmp_purchased_quantity
                amnt = rec.tmp_share.unitPrice * rec.tmp_purchased_quantity

                vls = {
                    'member_id': rec.member_id.id,
                    'share': share_id,
                    'purchased_quantity': share_quantity,
                    'total_amount': share_quantity * rec.tmp_share.unitPrice,
                    'purchased_date': rec.tmp_payment_date,
                    'company_id': rec.company_id.id,
                }

                mem_share = self.env['smif.member_shares'].save_member_share_sales(vls)
                if mem_share:
                    rec.tmp_share.save_shares_sales(share_quantity)

            values = {
                'payment_mode': rec.tmp_payment_mode,
                'account_id': acc_id,
                'loan_id': ln_id,
                'payment_journal_id': jorn_id,
                'company_id': rec.company_id.id,
                'payment_date': rec.tmp_payment_date,
                'check_number': chk,
                'payment_ref_number': payment_ref,
                'share': share_id,
                'purchased_quantity': share_quantity,
                'memb_divid': rec.id,
                'amount': amnt,
            }
            res = super(SmifDividendSettlement, mem_settl).create(values)
            if res:
                self.is_selected = False
            return res


def show_error_message(title, message_to_display):
    return show_message(title, message_to_display, 'danger')


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


class SmifDividendSettlement(models.Model):
    _name = 'smif.dividend_settlement'
    _description = 'Dividend Way of Settlement'

    # dividend_ids = fields.Many2one('smif.member_dividend', string='Dividend', index=True)
    mem_id = fields.Integer(string="Member ID", compute='on_member_change')

    payment_mode = fields.Selection(string="Mode of Settlement",
                                    selection=[('cash', 'Cash Payment'), ('loan', 'Loan Payment'),
                                               ('account', 'Account Transfer'), ('share', 'Share Purchase'), ],
                                    required=True, default='cash')

    account_id = fields.Many2one('smif.member_account', string='Account', domain="[('member_ids.id', '=', mem_id)]",
                                 select=True, )
    loan_id = fields.Many2one('smif.loan_request', string='Loan', domain="[('member_id.id', '=', mem_id)]")
    payment_journal_id = fields.Many2one('account.journal', string='Paid On',
                                         check_company=True, required=False)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    payment_date = fields.Date(string=' Date', default=datetime.now())
    payment_ref_number = fields.Char('Reference Number', store=True)
    check_number = fields.Char('Check Number', store=True)

    share = fields.Many2one('smif.shares', string='Share', )
    purchased_quantity = fields.Integer(string="Quantity", )

    memb_divid = fields.Many2one('smif.member_dividend', string='Member Dividend', index=True)

    # @api.onchange('payment_mode', )
    @api.depends('memb_divid')
    def on_member_change(self):
        for rec in self:
            rec.mem_id = rec.memb_divid.member_id.id
            # rec.amount = rec.memb_divid.remaining_amount

    amount = fields.Float(string='Amount', required=True, store=True, )

    #
    # @api.onchange('amount', )
    # def change_amount(self):
    #     for rec in self:
    #         if rec.amount <= 0:
    #             return  show_error_message("Invalid Amount Value, Amount has to be greater than Zero")
    #         elif rec.amount > rec.memb_divid.remaining_amount:
    #             return show_error_message("Amount Must not exceed Remaining Dividend")

    @api.model
    def create(self, values):
        res = ''
        if self.amount <= self.memb_divid.remaining_amount:
            res = show_error_message('Amount Must not exceed Remaining Dividend')
        elif self.amount <= 0:
            res = show_error_message('Invalid Amount Value, Amount has to be greater than Zero')
        else:
            res = super(SmifDividendSettlement, self).create(values)
        return res
