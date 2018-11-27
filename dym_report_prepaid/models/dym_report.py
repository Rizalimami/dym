from openerp import models, fields, api


class dym_report_account_prepaid(models.Model):
    _inherit = 'account.asset.asset'

    # override list in custom module to add/drop columns
    # or change order of the partner summary table
    def _report_xls_account_prepaid_fields(self, cr, uid, context=None):
        return [
            'no', \
            'branch_name', \
            'asset_code', \
            'asset_account', \
            'nomor_sin',\
            'category_name', \
            'asset_name', \
            # 'asset_owner',\
            'analytic_combination', \
            'analytic_1', \
            'analytic_2', \
            'analytic_3', \
            'analytic_4', \
            'purchase_value', \
            'depr_jan', \
            'depr_feb', \
            'depr_mar', \
            'depr_apr', \
            'depr_mei', \
            'depr_jun', \
            'depr_jul', \
            'depr_aug', \
            'depr_sep', \
            'depr_okt', \
            'depr_nop', \
            'depr_des', \
            'depr_ttloy', \
            'amortizatied_value', \
            'nbv', \
            'purchase_date', \
            'number_of_depr', \
            'depr_end_date', \
            'coa_depr_code', \
            'coa_depr_name', \
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
