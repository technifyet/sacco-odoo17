import base64

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from odoo.modules import get_module_resource


class SmifAddress(models.Model):
    _name = 'smif.address'
    _rec_name = 'address_name'
    _description = 'Address'
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = 'complete_name'
    _order = 'complete_name'

    address_name = fields.Char('Name', index='trigram', required=True)
    type = fields.Selection([('country', 'Country'), ('region', 'Region'), ('zone', 'Zone'),('city', 'City'), ('Sub-city', 'Sub City'),
                              ('woreda', 'Woreda'), ('kebele', 'Kebele'), ('village', 'Village'), ], string='Type', default='region',
                             required=True)
    parent_id = fields.Many2one('smif.address', 'Parent Address', index=True, ondelete='cascade')
    remark = fields.Char('Remark')
    # parent_address = fields.Many2one('smif.address', string='Parent Address', index=True)


    complete_name = fields.Char(
        'Complete Name', compute='_compute_complete_name', recursive=True,
        store=True)

    parent_path = fields.Char(index=True, unaccent=False)
    child_id = fields.One2many('smif.address', 'parent_id', 'Child Address')

    @api.depends('address_name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for address in self:
            if address.parent_id:
                address.complete_name = '%s / %s' % (address.parent_id.complete_name, address.address_name)
            else:
                address.complete_name = address.address_name

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError('You cannot create recursive categories.')

    @api.model
    def name_create(self, address_name):
        return self.create({'address_name': address_name}).name_get()[0]

    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.address_name) for record in self]
        return super().name_get()

    # @api.ondelete(at_uninstall=False)
    # def _unlink_except_default_category(self):
    #     main_address = self.env.ref('product.product_category_all')
    #     if main_address in self:
    #         raise UserError("You cannot delete this product category, it is the default generic category.")
    #     expense_category = self.env.ref('product.cat_expense')
    #     if main_address in self:
    #         raise UserError("You cannot delete the %s product category.", expense_category.address_name)
