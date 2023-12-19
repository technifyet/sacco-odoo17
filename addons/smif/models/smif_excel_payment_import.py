# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import io
import xlrd
import babel
import logging
import tempfile
import binascii
from io import StringIO
from datetime import date, datetime, time

# from addons.smif.models.smif_loan import SmifLoanInstallment
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Date

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ImportExcelPayment(models.Model):
    _name = 'smif.excel_payment_import'
    _description = 'Import Excel Payment'
    _rec_name = 'imported_date'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    file_type = fields.Selection([('CSV', 'CSV File'), ('XLS', 'XLS File')], string='File Type', default='XLS')
    file_content = fields.Selection([('Raw', 'Raw File'), ('Formatted', 'Formatted File')], string='File Content',
                                    default='Raw')

    status = fields.Selection(
        selection=[('creating', 'creating'), ('loaded', 'Loaded'), ('validated', 'Validated'),
                   ('imported', 'Imported'), ('rejected', 'Rejected')],
        string="Status", default='creating', tracking=True)

    file = fields.Binary(string="Upload File")

    data_lines = fields.One2many('smif.data_to_import', 'import_id', string='Data Lines', tracking=True)
    imported_date = fields.Date(string="Request Date", readonly=True, default=datetime.today())

    payment_journal_id = fields.Many2one('account.journal', string='Paid On', check_company=True)

    def import_payment(self):
        if self.payment_journal_id:
            for line in self.data_lines:
                line.affect_member_import()

            self.status = 'imported'
        else:
            notification = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Payroll Import',
                    'message': 'Please Selected Journal Entry',
                    'type': 'danger',  # types: success,warning,danger,info
                    'sticky': False,  # True/False will display for few seconds if false
                },
            }
            return notification

    def reject_import_payment(self):
        self.status = 'rejected'

    def load_and_validate_import(self):
        # self.create()
        if not self.file:
            raise ValidationError(_("Please Upload File to Import Payment !"))

        if self.file_type == 'CSV':
            keys = ['name', 'job_title', 'mobile_phone', 'work_phone', 'work_email', 'department_id',
                    'address_id', 'gender', 'birthday']
            try:
                csv_data = base64.b64decode(self.file)
                data_file = io.StringIO(csv_data.decode("utf-8"))
                data_file.seek(0)
                file_reader = []
                csv_reader = csv.reader(data_file, delimiter=',')
                file_reader.extend(csv_reader)
            except Exception:
                raise ValidationError(_("Please Select Valid File Format !"))

            values = {}
            for i in range(len(file_reader)):
                field = list(map(str, file_reader[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        res = self.create_import(values)
                        self.status = 'validated'
        else:
            try:
                file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                file.write(binascii.a2b_base64(self.file))
                file.seek(0)
                values = {}
                workbook = xlrd.open_workbook(file.name)
                sheet = workbook.sheet_by_index(0)
            except Exception:
                raise ValidationError(_("Please Select Valid File Format !"))

            for row_no in range(sheet.nrows):
                val = {}
                if row_no <= 0:
                    fields = list(map(lambda row: row.value.encode('utf-8'), sheet.row(row_no)))
                else:
                    line = list(
                        map(lambda row: isinstance(row.value, bytes) and row.value.encode('utf-8') or str(row.value),
                            sheet.row(row_no)))
                    values.update({
                        'sequence_number': line[0],
                        'member_id': line[1].replace('.0', ''),
                        'member_name': line[2],
                        'pay_zone': line[3],
                        #Todo: For now use last index  as  amount, but this should be configurable
                        'amount': line[fields.__len__()-1],
                        # 'forced_saving': line[5],  # 10% of amount
                        # 'current_saving': line[6],  # 2% of amount
                        # 'voluntary_saving': line[7],
                        # 'share': line[8],
                        # 'registration': line[9],
                        # 'child_saving': line[10],
                        # 'woman_saving': line[11],
                        # 'excel_total': line[12],
                        'import_id': self.id
                    })
                    res = self.create_import(values)
                    self.status = 'validated'

    def create_import(self, values):
        data_to_import = self.env['smif.data_to_import']
        res = data_to_import.prepare_data(values)
        return res


class SmifImportedMemberPayable(models.Model):
    _name = 'smif.imported_member_payable'
    _rec_name = 'payment_reason'
    _description = 'Import Member Payable Reasons'

    data_import_id = fields.Many2one('smif.data_to_import', string='Data Import ID')
    # reason = fields.Selection(
    #     selection=[('Registration', 'registration'), ('Share', 'share'), ('Loan', 'loan'),
    #                ('Account', 'account')], string="Reason")
    payment_reason = fields.Char(string='Reason')
    type = fields.Char(string="Type", )
    reason_ref_id = fields.Integer(string="Reason ID", required=False, )
    payable_amount = fields.Float(string="Payable Amount", required=True, default=0)
    paid_amount = fields.Float(string="Paid Amount", required=True, default=0)


class SmifDataToImport(models.Model):
    _name = 'smif.data_to_import'
    _rec_name = 'sequence_number'
    _description = 'Data To Import'

    import_id = fields.Many2one('smif.excel_payment_import', string='Import', index=True)
    sequence_number = fields.Char(string="Number", )
    member_id = fields.Char(string="Member ID", )
    member_name = fields.Char(string="Member Full Name", )
    pay_zone = fields.Char(string="Pay Zone Code", )
    amount = fields.Char(string="Amount", )
    forced_saving = fields.Char(string="Forced Saving", )
    current_saving = fields.Char(string="Current Saving", )
    voluntary_saving = fields.Char(string="Voluntary Saving", )
    share = fields.Char(string="Share", )
    registration = fields.Char(string="Registration Fee", )
    child_saving = fields.Char(string="Child Saving", )
    woman_saving = fields.Char(string="Woman Saving", )
    excel_total = fields.Char(string="Excel Total", )
    system_comment = fields.Char(string="System Comment", )
    ready_to_import = fields.Boolean(string="READY")

    payable_ids = fields.One2many('smif.imported_member_payable', 'data_import_id', string='Payable')

    member_loaded = fields.Many2one('smif.member', string='Member From SacoSys')

    def affect_member_loan(self, loan_pay):
        loan_inst = self.env['smif.loan_installment'].search([('id', '=', loan_pay.reason_ref_id)])
        inst_values = {}

        inst_values.__setitem__('payment_ref_number', "import-" + str(self.id))
        inst_values.__setitem__('paid_date', date.today())

        inst_values.__setitem__('payment_journal_id', self.import_id.payment_journal_id.id)
        inst_values.__setitem__('payment_transaction_note', 'Payroll Imported')
        inst_values.__setitem__('tmp_saving_amount', 0)
        inst_values.__setitem__('tmp_penalty_amount', 0)
        inst_values.__setitem__('tmp_loan_payment_amount', loan_pay.payable_amount)

        loan_inst.saveInstallmentPayment(inst_values)
        # super(SmifLoanInstallment, loan_inst).update(loan_inst)
        return True

    def affect_member_account(self, pay):
        res = False
        accounts = []
        curr_acc = []
        account_pay = self.env['smif.member_account'].search([('id', '=', pay.reason_ref_id)])
        member = account_pay.member_ids
        # account_pay.tmp_transaction_amount = pay.payable_amount
        # account_pay.tmp_transaction_date=date.today
        values = {}
        curr_acc.append(account_pay.id)
        curr_acc.append(account_pay.id)
        curr_acc.append({'tmp_transaction_amount': pay.payable_amount})

        accounts.append(curr_acc)
        values.__setitem__('tmp_journal_id', self.import_id.payment_journal_id.id)
        values.__setitem__('member_account_ids', accounts)
        values.__setitem__('tmp_transaction_note', 'Payroll Deposit')
        values.__setitem__('tmp_ref_number', "import-" + str(self.id))
        values.__setitem__('tmp_payment_method', 'bank')
        # {'tmp_journal_id': 7,
        #  'member_account_ids': [[1, 1, {'tmp_transaction_amount': 6550}], [4, 2, False], [4, 3, False]]}

        member.saveDepositTransaction(values)

        res = True
        return res

    def affect_member_import(self):
        res = False
        if self.ready_to_import:
            for payable in self.payable_ids:
                if payable.payment_reason == 'loan':
                    self.affect_member_loan(payable)
                    res = True
                elif payable.payment_reason == 'account':
                    self.affect_member_account(payable)
                    res = True
        return res

    def set_loan_payments_if_any(self, member, payable, payable_amount):
        res = False

        for loan_id in member.member_loan_ids:
            inst = loan_id.getNextPayableInstallment()
            if inst:
                amount = inst.total_installment_payment
                remaining = payable_amount - amount  # deduct from remaining  payable amount
                if remaining < 0:
                    amount = payable_amount
                    payable_amount = 0
                else:
                    payable_amount = remaining
                loan_pay = {
                    'payment_reason': 'loan',
                    'reason_ref_id': inst.id,
                    'type': inst.loan_request_id.loan_type_id.loan_type,
                    'data_import_id': self.id,
                    'payable_amount': amount,
                    'paid_amount': 0,
                }
                # loan_pays.append(loan_pay)
                super(SmifImportedMemberPayable, payable).create(loan_pay)
        return payable_amount
        # res=super(SmifImportedMemberPayable, payable).create(loan_pay)
        # res = True

    def get_payment_amount_for_acc(self, member, account):
        acc_type = account.account_type
        amount = 0
        if acc_type.minimum_saving_in == 'percentage':
            amount = acc_type.minimum_saving_amount * member.salary / 100
        elif acc_type.minimum_saving_in == 'amount':
            amount = acc_type.minimum_saving_amount

        return amount

    def set_account_depo_payments_if_any(self, member, payable, payable_amount):
        other_account = []
        for acct in member.member_account_ids:

            if acct.is_active and acct.account_type.is_compulsory_account:
                amount = self.get_payment_amount_for_acc(member, acct)
                remaining = payable_amount - amount  # deduct from remaining  payable amount
                if remaining < 0:
                    amount = payable_amount
                    payable_amount = 0
                else:
                    payable_amount = remaining
                acc_pay = {
                    'payment_reason': 'account',
                    'reason_ref_id': acct.id,
                    'type': acct.account_type.account_name,
                    'data_import_id': self.id,
                    'payable_amount': amount,
                    'paid_amount': 0,
                }
                super(SmifImportedMemberPayable, payable).create(acc_pay)
            elif acct.is_active:
                other_account.append(acct)

        if payable_amount > 0:
            for oth_acc in other_account:
                amount = self.get_payment_amount_for_acc(member, oth_acc)
                remaining = payable_amount - amount  # deduct from remaining  payable amount
                if remaining < 0:
                    amount = payable_amount
                    payable_amount = 0
                else:
                    payable_amount = remaining
                acc_pay = {
                    'payment_reason': 'account',
                    'reason_ref_id': acct.id,
                    'type': oth_acc.account_type.account_name,
                    'data_import_id': self.id,
                    'payable_amount': amount,
                    'paid_amount': 0,
                }
                super(SmifImportedMemberPayable, payable).create(acc_pay)
        return payable_amount  # Return remaining amount

    def get_member(self, member_id):
        member = self.env['smif.member'].search([('member_id_number', '=', member_id)])
        return member

    def is_data_valid(self, values):
        valid = False
        msg = ""
        if 'amount' in values:
            valid = type(values['amount']) == int or float
            if not valid:
                msg = "Invalid Amount, Not Number"
            elif float(values['amount']) <= 0:
                msg = "Invalid Amount, Must be greater than 0"
        else:
            msg = "Missing Amount Value"

        if valid and 'member_name' not in values:
            msg = 'Missing Member Name'
            valid = False  # Don't check next validation if this fails

        if valid and 'member_id' not in values:
            msg = 'Member Id Is Missing'
            valid = False  # Don't check next validation if this fails

        return msg

    def prepare_data(self, values):
        message = ""
        data_line_saved = super(SmifDataToImport, self).create(values)
        error_msg = self.is_data_valid(values)
        if not error_msg:
            full_name = values['member_name']
            member = self.get_member(values['member_id'])
            payable_amount = float(values['amount'])
            if member:
                data_line_saved.member_loaded = member.id
                if full_name != member.fullName:
                    full_name = member.fullName + "/" + full_name
                    message = "Name Mismatched"
                payable_amount = data_line_saved.set_loan_payments_if_any(member, data_line_saved.payable_ids,
                                                                          payable_amount)
                payable_amount = data_line_saved.set_account_depo_payments_if_any(member, data_line_saved.payable_ids,
                                                                                  payable_amount)
                valid = True

            else:
                message = "Member Not Found"
                valid = False

            values.update({
                'system_comment': message,
                'member_name': full_name,
                'ready_to_import': valid
            })
        else:
            message = "Data Validation Failed"
            values.update({
                'system_comment': message + " - " + error_msg,
                'ready_to_import': False
            })

        res = super(SmifDataToImport, data_line_saved).update(values)
