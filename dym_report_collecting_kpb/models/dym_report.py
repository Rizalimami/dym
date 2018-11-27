from openerp import models, fields, api

class dym_report_collecting_kpb(models.Model):
    _inherit = 'dym.collecting.kpb.line'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_collecting_kpb_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'number',\
            'no_claim_md',\
            'date',\
            'category',\
            'kpb_ke',\
            'no_wo',\
            'no_kartu',\
            'invoice_jasa_number',\
            'invoice_jasa_amount',\
            'invoice_oli_number',\
            'invoice_oli_amount',\
            'invoice_kompensasi_number',\
            'invoice_kompensasi_amount',\
            'total',\
            'state',\
        ]
 
    def _report_xls_collecting_kpb_mutasi_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'date',\
            'number',\
            'no_claim_md',\
            'qty_claim',\
            'sisa_nrfs',\
            'int_trf_date',\
            'int_trf_number',\
            'int_trf_qty',\
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
     