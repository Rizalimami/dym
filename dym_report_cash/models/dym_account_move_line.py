from openerp import models, fields, api

class dym_account_move_line(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_cash_non_status_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_code',\
            'tanggal',\
            'jam',\
            'kwitansi_name',\
            'account_code',\
            'keterangan',\
            'tunai',\
            'bank_check',\
            'edc',\
            'total',\
            'move_name'

        ]
        
    def _report_xls_cash_pettycash_fields(self, cr,uid,context=None):
        return [
            'no',\
            'tgl_konf',\
            'state',\
            'move_line_name',\
            'partner_name',\
            'keterangan',\
            'debit',\
            'credit',\
            'saldo',\
            'user_name',\
            'jam',\
                ]