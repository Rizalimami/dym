{
    "name":"Employee",
    "version":"1.0",
    "author":"ADSOFT",
    "category":"Custom Module for DYMS",
    "description": """
        Addons Employee
    """,
    "depends":[
        "base",
        "hr",
        "dym_address",
        "dym_branch",
        "hr_attendance"
    ],
    "data":[
        "views/dym_hr_employee_view.xml",
        "views/dym_hr_job_view.xml",
        "views/dym_hr_department.xml",
        # "security/res_groups.xml",
    ],
    "active":False,
    "installable":True
}
