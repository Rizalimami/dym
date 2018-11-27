{
    "name":"Closing Purchase Order",
    "version":"0.1",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Closing Purchase Order.
    """,
    "depends":["base", "purchase"],
    "data":[
        "data/cron.xml",
        "wizard/close_purchase.xml",
        "views/close_view.xml",
    ],
    "active":False,
    "installable":True
}
