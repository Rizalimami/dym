from openerp import models, fields, api

class dym_report_piutang_pajak_progresif_account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_piutang_pajak_progresif_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_name',\
            'division',\
            'invoice_origin',\
            'invoice_name',\
            'name',\
            'date_aml',\
            'due_date',\
            'partner_code',\
            'partner_name',\
            'cabang_partner',\
            'piutang_jpnett',\
            'finance_company',\
            'payment_type',\
            'overdue',\
            'status',\
            'saldo_awal',\
            'tot_invoice',\
            'amount_residual',\
            'current',\
            'overdue_1_3',\
            'overdue_4_7',\
            'overdue_8_30',\
            'overdue_31_60',\
            'overdue_61_90',\
            'overdue_91_n',\
            'reference',\
            'journal_name',\
            'account_code',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
        ]

    def _report_xls_piutang_pajak_progresif_fields_detail_pembayaran(self, cr, uid, context=None):
        return [
            'no',\
            'branch_status',\
            'branch_name',\
            'division',\
            'invoice_origin',\
            'invoice_name',\
            'name',\
            'date_aml',\
            'due_date',\
            'partner_code',\
            'partner_name',\
            'finance_company',\
            'overdue',\
            'status',\
            'saldo_awal',\
            'tot_invoice',\
            'pay_date',\
            'pay_no',\
            'pay_retur',\
            'pay_pindahan',\
            'pay_amount',\
            'amount_residual',\
            'current',\
            'overdue_1_3',\
            'overdue_4_7',\
            'overdue_8_30',\
            'overdue_31_60',\
            'overdue_61_90',\
            'overdue_91_n',\
            'reference',\
            'journal_name',\
            'account_code',\
            'analytic_combination',\
            'analytic_1',\
            'analytic_2',\
            'analytic_3',\
            'analytic_4',\
        ]
 
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_arap_details_fields(self, cr, uid, context=None):
        return [
            'document', 'date', 'date_maturity', 'account', 'description',
            'rec_or_rec_part', 'debit', 'credit', 'balance',
            # 'partner_id',
        ]
 
    # Change/Add Template entries
    def _report_xls_arap_overview_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
 
    # Change/Add Template entries
    def _report_xls_arap_details_template(self, cr, uid, context=None):
        """
        Template updates, e.g.
 
        my_change = {
            'partner_id':{
                'header': [1, 20, 'text', _('Move Line ID')],
                'lines': [1, 0, 'text', _render("p['ids_aml']")],
                'totals': [1, 0, 'text', None]},
        }
        return my_change
        """
        return {}
     