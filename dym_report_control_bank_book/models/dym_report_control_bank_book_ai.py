from openerp import models, fields, api 

class dym_report_control_bank_book_ai(models.Model):
    _inherit = 'account.move.line'
    
    def _report_xls_control_bank_book_fields(self, cr, uid, context=None):
        return [
            'no',\
            'period',\
            'company_name',\
            'branch_name',\
            'account_code',\
            'account_name',\
            'saldo_bank_book',\
            'saldo_general_ledger',\
            'penjelasan',\
        ]
    