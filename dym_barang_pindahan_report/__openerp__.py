{
    "name" : "DYM Laporan Barang Pindahan",
    "version" : "0.1",
    "sequence": 2,
    "description": """
        Laporan Barang Pindahan.
    """,
    "depends" : [
        "dym_serial_number","report",
    ],
    "data" : [
        "views/barang_pindahan_report.xml",
        "wizard/wizard_barang_pindahan_report.xml",
        "report/report_barang_pindahan_report.xml",
    ],
    "installable" : True,
    "application" : True,
}
