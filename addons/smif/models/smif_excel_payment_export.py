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

# from addons.smif.models.smif_loan Export SmifLoanInstallment
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Date

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `Export csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `Export xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `Export cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `Export base64`.')


class ExportExcelPayment(models.Model):
    _name = 'smif.excel_payment_export'
    _description = 'Export Excel Payment'
    _rec_name = 'exported_date'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    title = fields.Char('Title')
    data_lines = fields.One2many('smif.data_to_export', 'export_id', string='Data Lines', tracking=True)
    exported_date = fields.Date(string="Export Date", readonly=True, default=datetime.today())
    pay_zone_id = fields.Many2one('smif.pay_zone', string='Pay Zone', index=True, tracking=True)
    company_id = fields.Many2one('res.company', 'Company')
    department_id = fields.Many2one('hr.department', 'Department',
                                    domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    def _default_item_orders(self):
        # Loan, Forced
        # Saving, Current
        # '
        # 'saving,Voluntary saving,Share,Registration,'
        # 'Children Saving,Woman saving,Total'
        value = ""
        loan_typs = self.env['smif.loan_type'].search([])
        for lnt in loan_typs:
            value = value + lnt.loan_type+ ","
            # value = value + "Loan" + ","  # Loan is summed up
            # break

        acc_types = self.env['smif.account_type'].search([])
        for act in acc_types:
            value = value + act.account_name + ","
        value = value + "Total"
        return value

    item_orders = fields.Char('Export Orders', required=True, default=_default_item_orders,
                              help="Enter Comma Separated Column Names", )

    def generate_payments(self):
        params = []
        if self.company_id:
            params.append(('company_id', '=', self.company_id.id))
        if self.pay_zone_id:
            params.append(('pay_zone_id', '=', self.pay_zone_id.id))
        if self.department_id:
            params.append(('department_id', '=', self.department_id.id))

        members = self.env['smif.member'].search(params)
        count = 1;
        for exp in self.data_lines:
            exp.unlink()

        for memb in members:
            data_to_export = self.env['smif.data_to_export']
            values = {}
            values.update({
                'sequence_number': str(count),
                'member_id': memb.member_id_number,
                'member_name': memb.fullName,
                'pay_zone': memb.pay_zone_id.pay_zone_code,
                'amount': 0,
                'export_id': self.id
            })
            count = count + 1
            res = data_to_export.create_export_line(values, memb)
        return members

    def get_export_lines_sum_only(self):
        output = "Number,Member ID, Member Name, Pay Zone, Total Amount, Remark"
        for line in self.data_lines:
            payzon_code = "NA"
            if line.pay_zone:
                payzon_code = line.pay_zone

            output = output + "\n" + line.sequence_number + "," + line.member_id + "," + line.member_name + "," + payzon_code + "," + line.amount
        return output

    def get_export_lines_details(self):
        # S.N | ID | Name| PZ | Cr.Ln | Forced Saving (10%) | Current saving (2%) | Voluntary saving  | Share | Registration | Children Saving | Woman saving | Total

        columns = "Number,Member ID, Member Name, Pay Zone"
        output = ""
        items = self.item_orders.split(",")

        for line in self.data_lines:
            payzon_code="-"
            if line.pay_zone:
                payzon_code = line.pay_zone

            payable_items = {'S.N': str(line.sequence_number), 'ID': line.member_id, 'Member Name': line.member_name,
                             'PZ': payzon_code}


            for pay in line.payable_ids:
                payable_items[pay.type.lower()] = pay.payable_amount

            payable_items['total'] = line.amount

            output = output + "\n" + payable_items['S.N'] + "," + payable_items['ID'] + "," + payable_items[
                'Member Name'] + "," + payable_items['PZ']

            for itm in items:
                if(payable_items.__contains__(itm.lower())):
                    output = output + "," + str(payable_items[itm.lower()])
                else:
                    output = output + "," + ""
        # Prepare remaining columns based on set value from ui
        for colm in items:
            columns = columns + "," + colm

        return columns + "\n" + output

    def export_payment(self):
        file_name = "Member_Payroll_Deduction"
        if self.title:
            file_name = self.title
        file_name = file_name + "_" + str(self.exported_date) + ".xlsx"

        # output is where you have the content of your file, it can be
        # any type of content

        # output = self.get_export_lines_sum_only()
        output = self.get_export_lines_details()

        # encode
        result = base64.b64encode(str(output).encode('UTF-8'))
        # get base url
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        # create attachment
        attachment_id = attachment_obj.create({'name': file_name, 'datas': result})
        # prepare download url
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        # download
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }


class SmifExportedMemberPayable(models.Model):
    _name = 'smif.exported_member_payable'
    _rec_name = 'payment_reason'
    _description = 'Export Member Payable Reasons'

    data_export_id = fields.Many2one('smif.data_to_export', string='Data Export ID')
    payment_reason = fields.Char(string='Reason')
    type = fields.Char(string="Type", )
    reason_ref_id = fields.Integer(string="Reason ID", required=False, )
    payable_amount = fields.Float(string="Payable Amount", required=True, default=0,digits=(12,2))


class SmifDataToExport(models.Model):
    _name = 'smif.data_to_export'
    _rec_name = 'sequence_number'
    _description = 'Data To Export'

    export_id = fields.Many2one('smif.excel_payment_export', string='Export', index=True)
    sequence_number = fields.Char(string="Number", )
    member_id = fields.Char(string="Member ID", )
    member_name = fields.Char(string="Member Full Name", )
    pay_zone = fields.Char(string="Pay Zone Code", )
    amount = fields.Char(string="Total", )
    payable_ids = fields.One2many('smif.exported_member_payable', 'data_export_id', string='Payable')
    member_loaded = fields.Many2one('smif.member', string='Member From SaccoSys')

    def create_export_line(self, values, member):
        total_payable = 0
        data_line_saved = super(SmifDataToExport, self).create(values)
        # calculate all member payable and update total amount
        total_payable = total_payable + data_line_saved.set_loan_payments_if_any(member, data_line_saved.payable_ids)
        total_payable = total_payable + data_line_saved.set_account_depo_payments_if_any(member,
                                                                                         data_line_saved.payable_ids)

        if total_payable > 0:
            values.update({
                'amount': total_payable,
            })
            res = super(SmifDataToExport, data_line_saved).update(values)

    def set_loan_payments_if_any(self, member, payable):
        total_payable = 0

        for loan_id in member.member_loan_ids:
            inst = loan_id.getNextPayableInstallment()
            if inst:
                amount = inst.total_installment_payment
                loan_pay = {
                    'payment_reason': 'loan',
                    'reason_ref_id': inst.id,
                    'type': inst.loan_request_id.loan_type_id.loan_type,
                    'data_export_id': self.id,
                    'payable_amount': amount
                }
                total_payable = total_payable + amount

                super(SmifExportedMemberPayable, payable).create(loan_pay)
        return total_payable

    def get_payment_amount_for_acc(self, member, account):
        acc_type = account.account_type
        amount = 0
        if acc_type.minimum_saving_in == 'percentage':
            amount = acc_type.minimum_saving_amount * member.salary / 100
        elif acc_type.minimum_saving_in == 'amount':
            amount = acc_type.minimum_saving_amount

        return amount

    def set_account_depo_payments_if_any(self, member, payable):
        payable_amount = 0
        for acct in member.member_account_ids:

            if acct.is_active and acct.account_type.is_compulsory_account:
                amount = self.get_payment_amount_for_acc(member, acct)

                acc_pay = {
                    'payment_reason': 'account',
                    'reason_ref_id': acct.id,
                    'type': acct.account_type.account_name,
                    'data_export_id': self.id,
                    'payable_amount': amount
                }
                payable_amount = payable_amount + amount
                super(SmifExportedMemberPayable, payable).create(acc_pay)
        return payable_amount  # Return remaining amount
