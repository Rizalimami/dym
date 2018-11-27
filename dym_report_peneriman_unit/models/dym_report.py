from openerp import models, fields, api

class dym_report_penerimaan_unit(models.Model):
    _inherit = 'dym.stock.packing'
    
    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_penerimaan_unit_fields(self, cr, uid, context=None):
        return [
            'no',\
            'branch_id',\
            'supplier',\
            'number',\
            'date',\
            'surat_jalan',\
            'supplier_invoice_number',\
            'document_date',\
            'product_code',\
            'posisi',\
            'mesin',\
            'rangka',\
            'price_unit',\
            'discount',\
            'ap_unit',\
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
     