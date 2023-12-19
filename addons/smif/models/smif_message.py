from odoo import models, fields, api
class SmifMessage(models.TransientModel):
    _name = 'smif.message'

    title=fields.Char('Title', default='Validation Error')
    message=fields.Char('Message')

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}