# -*- coding: utf-8 -*-
# from odoo import http


# class Digmif(http.Controller):
#     @http.route('/smif/smif/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/smif/smif/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('smif.listing', {
#             'root': '/smif/smif',
#             'objects': http.request.env['smif.smif'].search([]),
#         })

#     @http.route('/smif/smif/objects/<model("smif.smif"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('smif.object', {
#             'object': obj
#         })
