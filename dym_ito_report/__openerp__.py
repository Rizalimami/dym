{
    "name" : "DYM Laporan ITO",
    "version" : "0.1",
    "sequence": 2,
    "description": "DYM Laporan ITO",
    "depends" : [
        "stock","report", "dym_branch",
    ],
    "data" : [
        "views/ito_report.xml",
        "wizard/wizard_ito_report.xml",
        "report/report_ito_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
