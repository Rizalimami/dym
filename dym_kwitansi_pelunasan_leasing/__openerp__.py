{
    "name" : "DYM Kwitansi Pelunasan Leasing",
    "version" : "0.1",
    "sequence": 2,
    "description": """
        Kwitansi Pelunasan Leasing.
    """,
    "depends" : [
        "dealer_sale_order",
        "report",
    ],
    "data" : [
        "views/kwitansi_pelunasan_leasing.xml",
        "wizard/wizard_kwitansi_pelunasan_leasing.xml",
        "report/report_kwitansi_pelunasan_leasing.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
    ],
    "installable" : True,
    "application" : True,
}
