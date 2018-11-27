{
    "name":"CI Opbal",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """This module aim to override normal operation in making consolidated invoice due to the absence of 
    picking_id since the products was not received in Odoo, but received on outside odoo instead.        
    """,
    "depends":[
        "dym_hpp",
        "dym_account_voucher",
    ],
    "data":[
        "views/hpp_view.xml",
        "views/lot_view.xml",
    ],
    "active":False,
    "installable":True
}
