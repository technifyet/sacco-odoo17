from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SmifPayZone(models.Model):
    _name = 'smif.pay_zone'
    _rec_name = 'pay_zone'
    _description = 'Pay Zone'

    pay_zone_code = fields.Char(string="Zone Code", required=True, )
    pay_zone = fields.Char(string="Pay Zone", required=True, )

