{
    "name" : "DYM Laporan Aging Bon",
    "version" : "0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "sequence": 2,
    "description": """
        Laporan Aging Bon.
    """,
    "depends" : [
        "dym_advance_payment",
        "report",
    ],
    "data" : [
        "views/aging_bon_report.xml",
        "wizard/wizard_aging_bon_report.xml",
        "report/report_aging_bon_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
