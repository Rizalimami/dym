
{
    "name":"DYM AHASS",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        
    """,
    "depends":[
        "dym_branch",
        "dym_bank_trf_request",
    ],
    "data":[
        "security/ir.model.access.csv",
        "views/dym_branch_view.xml",
        "views/dym_bank_trf_advice_view.xml",
        "views/dym_bank_transfer_view.xml",
        "views/dym_branch_config_view.xml",
        "views/dym_ahass_deposit_view.xml",
        "wizard/bank_trf_advice_group_view.xml",
    ],
    "active":False,
    "installable":True
}
