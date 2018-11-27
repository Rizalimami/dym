{
    "name" : "Holiday in a year",
    'summary': 'List of holidays in a year',
    "version" : "1.0",
    "depends" : ["hr","base"],
    "author" : "ADSOFT",
    "description": """This module is aimed to input holidays in a year.
    """,
    "website" : "https://adsoft.co.id",
    "category" : "Custom/Human Resources",
    "data" : [
       "views/hr_holiday_year_view.xml",
       "security/hr_holiday_security.xml",
       "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True,
}