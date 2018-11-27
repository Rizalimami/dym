{
    "name" : "DYM Laporan Kinerja Mekanik",
    "version" : "0.1",
    "sequence": 2,
    "description": """
        Laporan Kinerja Mekanik.
    """,
    "depends" : [
        "dym_work_order","report",
    ],
    "data" : [
        "views/kinerja_mekanik_report.xml",
        "wizard/wizard_kinerja_mekanik_report.xml",
        "report/report_kinerja_mekanik_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
