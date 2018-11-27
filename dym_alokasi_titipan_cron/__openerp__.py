{
    "name":"DYM Alokasi Customer Deposit - Cron",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """This module aim to validate Alokasi Customer Deposit document 
    via Cron Job Scheduler
    """,
    "depends":[
        "dym_alokasi_titipan_opbal",
    ],
    "data":[
        'data/validate_alokasi_customer_deposit.xml',
    ],
    "active":False,
    "installable":True
}
