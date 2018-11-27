{
    "name":"DYM Update Supplier Invoice Info",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """This module aim to enable user to update supplier invoice number and or date given by supplier on odoo supplier invoice form
    """,
    "depends":[
        "dym_account","account"
    ],
    "data":[
        "wizard/update_supplier_invoice_info.xml",
        "views/account_invoice_view.xml",
    ],
    "active":False,
    "installable":True
}