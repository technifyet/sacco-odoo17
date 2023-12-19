import base64

from odoo import models, fields, api
from odoo.modules import get_module_resource


class SmifFamily(models.Model):
    _name = 'smif.family'
    _rec_name = 'fullName'
    _description = 'Smart Microfinance Members Family'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_image(self):
        image_path = get_module_resource('smif', 'static/src/img', 'default_image.png')
        return base64.b64encode(open(image_path, 'rb').read())

    title_id = fields.Many2one('res.partner.title', string='Title')

    parent_member_id = fields.Many2one('smif.member',#,
                                       string='Member', index=True)

    fullName = fields.Char(string="Full Name", required=True, tracking=True)  # This is Member Full Name
    gender = fields.Selection(string="Gender", selection=[('male', 'Male'), ('female', 'Female'), ],
                              required=True, default='male')
    marital = fields.Selection([('single', 'Single'), ('married', 'Married'), ('widower', 'Widower'),
                                ('divorced', 'Divorced'), ], string='Marital Status', default='single',
                               required=True, tracking=True)
    dob = fields.Date(string="Date Of Birth", required=True, tracking=True)
    work_phone = fields.Char('Work Phone')
    mobile_phone = fields.Char('Work Mobile')
    email_address = fields.Char('Email Address')
    national_id = fields.Char('National ID')
    # family_count = fields.Integer(string="Number of Family", required=False, )
    active = fields.Boolean('Active', default=True, store=True, )

    relation_ship = fields.Selection([('child', 'Child'), ('spouse', 'Spouse'), ('father', 'Father'),
                                      ('mother', 'Mother'), ('other', 'Other')], string='Relation Ship',
                                     default='other', required=False, tracking=False)
    # parent_id = fields.Many2one('smif.member', string='Parent', index=True)
    # parent_name = fields.Char(related='parent_id.name', readonly=True, string='Parent name')
    # child_ids = fields.One2many('smif.member', 'parent_id', string='Inheritor', domain=[('active', '=', True)])
    additional_note = fields.Text(string='Additional Note', tracking=True)
    person_photo = fields.Image(default=_default_image, store=True, attachment=True)
    is_inheritor = fields.Boolean('Is Inheritor', default=True, store=True, )
