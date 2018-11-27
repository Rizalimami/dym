{
    "name" : "DYM Laporan Transfer Asset",
    "version" : "0.1",
    "sequence": 2,
    "description": "DYM Laporan Transfer Asset",
    "depends" : [
        "dym_purchase_asset","report",
    ],
    "data" : [
        "views/transfer_asset_report.xml",
        "wizard/wizard_transfer_asset_report.xml",
        "report/report_transfer_asset_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
