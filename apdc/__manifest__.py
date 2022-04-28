# -*- coding: utf-8 -*-
{
    'name': "APDC Module",

    'summary': """
        APDC Modules""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Omniswift Limited",
    'website': "https://www.omniswift.com/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Real Estate',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['base','hr', 'sale_crm', 'web', 'website_crm','purchase', 'crm' , 'product' , 'stock', 'sale_management', 'account_accountant'],
    # always loaded
    'data': [
        'security/apdc_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/views.xml',
        #'controller/document_portal_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        #'demo/demo.xml',
    ],
    
    'qweb': [
        #'views/chatter.xml'
    ],
    'images': [
        'static/description/icon.png',
    ],
    'images': ['static/description/icon.png'],
    "installable": True,
    "auto_install":False,
}
