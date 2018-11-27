{
    "name" : "DYM Laporan Kinerja Salesman",
    "version" : "0.1",
    "sequence": 2,
    "depends" : [
        "dealer_sale_order",
        "report",
    ],
    "description": """
        Laporan Kinerja Salesman.
    """,
    "data" : [
        "views/kinerja_salesman_report.xml",
        "wizard/wizard_kinerja_salesman_report.xml",
        "report/report_kinerja_salesman_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
