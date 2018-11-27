{
    "name" : "DYM Kwitansi GC",
    "version" : "0.1",
    "sequence": 2,
    "description": """
        Kwitansi GC.
    """,
    "depends" : [
        "dealer_sale_order",
        "report",
    ],
    "data" : [
        "views/kwitansi_gc.xml",
        "wizard/wizard_kwitansi_gc.xml",
        "report/report_kwitansi_gc.xml",
        "security/ir.model.access.csv",
        # "security/res_groups.xml",
    ],
    "installable" : True,
    "application" : True,
}
