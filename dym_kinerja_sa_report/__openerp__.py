{
    "name" : "DYM Laporan Kinerja Service Advisor",
    "version" : "0.1",
    "sequence": 2,
    "description": """
        Laporan Kinerja Service Advisor.
    """,
    "depends" : [
        "dym_work_order","report",
    ],
    "data" : [
        "wizard/wizard_kinerja_sa_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
