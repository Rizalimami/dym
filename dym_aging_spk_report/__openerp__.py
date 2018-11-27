{
    "name" : "DYM Laporan Aging Memo",
    "version" : "0.1",
    "sequence": 2,
    "description": """
        Laporan Aging Memo.
    """,
    "depends" : [
        "dealer_sale_order",
        "report",
    ],
    "data" : [
        "views/aging_spk_report.xml",
        "wizard/wizard_aging_spk_report.xml",
        "report/report_aging_spk_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
