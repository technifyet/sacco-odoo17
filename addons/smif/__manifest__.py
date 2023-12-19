# -*- coding: utf-8 -*-
{
    'name': "Digital Saccos Solutions",

    'summary': """
        SacoSys Digital Solutions that works for any size sacco""",

    'description': """
        Saving and Credit Associations Software Solution 
    """,

    'author': "Technify Ethiopia Solutions",
    'website': "http://www.technify.et",
    'category': 'Saving',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base','digest', 'mail'],

    # always loaded
    'data': [
        'security/smif_security.xml',
        'security/ir.model.access.csv',
        'views/smif_member_view.xml',
        'views/smif_transaction_view.xml',
        'views/smif_share_view.xml',
        'views/smif_account_view.xml',
        'views/smif_loan_payment_view.xml',
        'views/smif_loan_view.xml',
        'views/smif_pay_zone_view.xml',
        'views/res_config_settings_view.xml',
        'views/smif_deposit_tran_view.xml',
        'views/smif_withdrawal_tran_view.xml',
        'views/smif_transfer_tran_view.xml',
        'views/smif_member_loan_view.xml',
        'views/smif_message_view.xml',
        'views/smif_excel_payment_import_view.xml',
        'views/smif_address_view.xml',
        'views/smif_excel_payment_export_view.xml',
        'views/smif_dividend_view.xml',
        'views/smif_interest_view.xml',
        'views/smif_menu_view.xml'

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True
}
