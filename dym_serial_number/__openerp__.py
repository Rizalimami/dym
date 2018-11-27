{
    "name":"Master Serial Number",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Tambah Field
    """,
    "depends":[
        "base",
        "sale",
        "stock",
        "purchase",
        "dym_branch",
    ],
    "data":[
        "views/dym_serial_number_view.xml",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}