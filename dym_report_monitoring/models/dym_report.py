from openerp import models, fields, api

class dym_report_monitoring(models.Model):
    _inherit = 'purchase.order'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_monitoring_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_name', \
            'division', \
            'no_sugor', \
            'qty_sugor', \
            'tgl_pr',\
            'no_pr',\
            'qty_pr',\
            'tgl_po',\
            'no_po',\
            'qty_po',\
            'amount_po',\
            'tgl_bpb',\
            'no_bpb',\
            'qty_bpb',\
            'tgl_inv',\
            'no_inv',\
            'qty_inv',\
            'amount_inv',\
            'tgl_consol',\
            'no_consol',\
            'qty_consol',\
            'amount_consol',\
            'tgl_pay',\
            'no_pay',\
            'amount_pay',\
            'status'
        ]
 
    def _report_xls_monitoring_fields_detail_tipe(self, cr, uid, context=None):
        return [
            'no',\
            'branch_name', \
            'division', \
            'tipe_product', \
            'internal_reference', \
            'warna', \
            # 'no_sugor', \
            # 'qty_sugor', \
            'tgl_pr',\
            'no_pr',\
            'qty_pr',\
            'tgl_po',\
            'no_po',\
            'qty_po',\
            # 'amount_po',\
            # 'tgl_bpb',\
            # 'no_bpb',\
            'qty_bpb',\
            # 'tgl_inv',\
            # 'no_inv',\
            'qty_inv',\
            # 'amount_inv',\
            # 'tgl_consol',\
            # 'no_consol',\
            'qty_consol',\
            # 'amount_consol',\
            # 'tgl_pay',\
            # 'no_pay',\
            # 'amount_pay'
            'status'
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
     