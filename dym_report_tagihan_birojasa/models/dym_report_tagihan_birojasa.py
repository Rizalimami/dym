from openerp import models, fields, api

class dym_report_tagihan_birojasa(models.Model):
    _inherit = 'dym.proses.birojasa'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_tagihan_birojasa_fields(self, cr, uid, context=None):
        return [
                'no',
                'trans_no',
                'branch_name',
                'partner_name',
                'invoice_tagihan_number',
                'invoice_tagihan_date',
                'invoice_dso_number',
                'invoice_dso_date',
                'nosin',
                'notice',
                'jasa',
                'total_estimasi',
                'pajak_progressive',
                'total_tagihan',
                'titipan',
                'piutang_dagang_stnk',
                'koreksi',
                'margin',
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
     