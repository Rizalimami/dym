{
    "name":"Pengurusan STNK dan BPKB",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Permohonan Faktur
    """,
    "depends":[
        "base",
        "account",
        "stock",
        "dym_dealer_menu",
        "dym_serial_number",
        "product"
    ],
    "data":[  
        "views/dym_pengurusan_sntk_bpkb_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",    
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",            
        "views/dym_pengurusan_stnk_bpkb_workflow.xml",
        "views/dym_serial_number_pf_view.xml",
        "views/dym_branch_config_view.xml",
        # "data/dym.branch.config.xml"          
    ],
    "active":False,
    "installable":True
}