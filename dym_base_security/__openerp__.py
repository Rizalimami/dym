{
    "name":"DYM User Group",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        User Groups
    """,
    "depends":[
        'base',
        'dym_base',
    ],
    "data":[
        "security/base_security.xml",
        "security/finance.xml",
        "security/general_affair.xml",
        "security/showroom.xml",
        "security/stnk.xml",
        "security/workshop.xml",
        "security/ir.model.access.csv",
    ],
    "active":False,
    "installable":True
}