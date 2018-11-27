from openerp import models, fields, api

class dym_account_move_line(models.Model):
    _inherit = 'account.move.line'

    def _report_xls_journal_detail_account_fields(self, cr, uid, context=None):
        return [
            'no',\
            'perid_code',\
            'account_code',\
            'account_name',\
            'branch_status',\
            'branch_name',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
            'analytic_konsolidasi',\
            'division',\
            # 'account_sap',\
            'tanggal',\
            'no_sistem',\
            'no_bukti',\
            'keterangan',\
            'debit',\
            'credit',\
            'reconcile_name',\
            'journal_name',\
            'partner_code',\
            'partner_name',\
            'cust_suppl', \
            'branch_x', \
            ]