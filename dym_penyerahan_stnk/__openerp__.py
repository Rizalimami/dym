{
    "name":"Penyerahan STNK dan BPKB",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Penyerahan STNK dan BPKB
    """,
    "depends":[
        "base",
        "dym_branch",
        "stock",
        "dym_dealer_menu",
        "dym_serial_number",
        "dym_jumlah_cetak"
    ],
    "data":[
        "report/report_penyerahan_bpkb.xml",
        "report/report_penyerahan_stnk.xml",
        "report/report.xml",
        "views/dym_penyerahan_stnk_report.xml",
        "views/dym_penyerahan_stnk_view.xml",
        "views/dym_penyerahan_bpkb_view.xml",
        "views/dym_serial_number_pf_view.xml",
        "security/ir.model.access.csv",
        "security/ir_rule.xml",         
        # "security/res_groups.xml",
        # "security/res_groups_button.xml",   
    ],
    "active":False,
    "installable":True
}