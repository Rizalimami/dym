from openerp import models, fields, api 

class dym_report_lbb_ai(models.Model):
    _inherit = 'dym.work.order'
    
    def _report_xls_lbb_fields(self, cr, uid, context=None):
        return [
            'no',\
            'type',\
            'total_unit_entry',\
            'kpb_1',\
            'kpb_2',\
            'kpb_3',\
            'kpb_4',\
            'kpb_5',\
            'claim',\
            'qs_cs',\
            'qs_ls',\
            'qs_or',\
            'lr',\
            'hr',\
            'total',\
            'jr',\
            'member_card',\
            'drive_thru',\
            'unit_safety'
        ]
    