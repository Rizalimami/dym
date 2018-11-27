# -*- coding: utf-8 -*-
{
    'name': "Proses Birojasa Update",

    'summary': """
        Custom Module DYM Proses Birojasa
        """,

    'description': """
        Custom Module DYM Proses Birojasa
    """,

    'author': "Arif Mustaqim",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Custom Module',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        "product",
        'dym_proses_stnk',
        'dym_opbal',
    ],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/dym_proses_birojasa_up.xml',
    ],
}