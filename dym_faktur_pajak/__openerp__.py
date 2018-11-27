{
    "name":"Faktur Pajak",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Generate Faktur Pajak
    """,
    "depends":[
        "base",
        "dym_branch",
        "dym_sequence",
        "dym_dealer_menu",
        "dym_register_kwitansi",
        # "dym_res_partner",
        "dym_approval"
    ],
    "data":[        
        "security/ir.model.access.csv",
        # "data/dym_remark_data.xml",
        "data/dym_signature_data.xml",
        "views/dym_faktur_pajak_report.xml",
        # "report/dym_faktur_pajak_report.rml",
        # "report/dym_faktur_pajak_report.rml",
        "views/dym_faktur_pajak_view.xml",
        "views/dym_signature_view.xml",
        "views/dym_remark_view.xml",
        "views/dym_generate_faktur_pajak_view.xml",
        "views/dym_faktur_pajak_gabungan_view.xml",
        "views/dym_faktur_pajak_other_view.xml",
        "wizard/wizard_efaktur.xml",
        "security/res_groups.xml",
        "security/res_groups_button.xml",
    ],
    "active":False,
    "installable":True
}
