from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


class dym_report_account_prepaid_print(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_account_prepaid_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
        })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        account_ids = data['account_ids']
        branch_status = False
        category_ids = data['category_ids']

        title_prefix = ''
        title_short_prefix = ''

        report_account_prepaid = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Prepaid')}

        query_start = """
                    SELECT
                    b.name as branch_name,
                    ass.id as asset_id,
                    ass.code as asset_code,
                    ass.name as asset_name,
                    c.name as category_name,
                    aac.name as asset_account,
                    ai.number as nomor_sin,
                    sales.name as asset_owner,
                    a1.code ||'/'|| a2.code ||'/'|| a3.code ||'/'|| a4.code analytic_combination,
                    a1.name analytic1_name,
                    a2.name analytic2_name,
                    a3.name analytic3_name,
                    a4.name analytic4_name,
                    ass.real_purchase_value as purchase_value,
                    sum(
                    case when to_char(depreciation_date,'mm') = '01' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) jan,
                    sum(
                    case when to_char(depreciation_date,'mm') = '02' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) feb,
                    sum(
                    case when to_char(depreciation_date,'mm') = '03' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) mar,
                    sum(
                    case when to_char(depreciation_date,'mm') = '04' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) apr,
                    sum(
                    case when to_char(depreciation_date,'mm') = '05' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) mei,
                    sum(
                    case when to_char(depreciation_date,'mm') = '06' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) jun,
                    sum(
                    case when to_char(depreciation_date,'mm') = '07' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) jul,
                    sum(
                    case when to_char(depreciation_date,'mm') = '08' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) aug,
                    sum(
                    case when to_char(depreciation_date,'mm') = '09' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) sep,
                    sum(
                    case when to_char(depreciation_date,'mm') = '10' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) okt,
                    sum(
                    case when to_char(depreciation_date,'mm') = '11' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) nop,
                    sum(
                    case when to_char(depreciation_date,'mm') = '12' and to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) des,
                    sum(
                    case when to_char(depreciation_date,'yyyy') = to_char(now(),'yyyy')
                    then dl.amount
                    end) ttloy,
                    ass.real_purchase_date as purchase_date,
                    max(dl.depreciation_date) depr_end_date,
                    a.code as coa_depr_code,
                    a.name as coa_depr_name,
                    ass.state as status,
                    ass.method_number as number_of_depr,
                    dlo.remaining_value nbv
                    FROM account_asset_asset ass
                    inner join account_analytic_account a1 on a1.id=ass.analytic_1
                    inner join account_analytic_account a2 on a2.id=ass.analytic_2
                    inner join account_analytic_account a3 on a3.id=ass.analytic_3
                    inner join account_analytic_account a4 on a4.id=ass.analytic_4
                    LEFT JOIN dym_branch b ON ass.branch_id = b.id
                    LEFT JOIN hr_employee emp ON ass.asset_user = emp.id
                    LEFT JOIN resource_resource sales ON emp.resource_id = sales.id
                    LEFT JOIN account_asset_category c ON ass.category_id = c.id
                    LEFT JOIN account_account a ON c.account_depreciation_id = a.id
                    LEFT JOIN account_asset_depreciation_line dl on dl.asset_id = ass.id
                    lEFT JOIN account_account aac ON c.account_asset_id = aac.id
                    LEFT JOIN purchase_order po ON ass.purchase_id = po.id
                    LEFT JOIN account_invoice ai ON po.name = ai.origin
                    left join (
                    with initx as (
                        select asset_id, max(depreciation_date) as depreciation_date
                        from account_asset_depreciation_line
                        where move_check='t'
                        group by asset_id)
                    select d.asset_id, d.remaining_value
                    from account_asset_depreciation_line d
                    inner join initx on d.asset_id=initx.asset_id and d.depreciation_date=initx.depreciation_date
                    where move_check='t'
                    ) dlo on dlo.asset_id=ass.id
                    where 1=1 AND c.type = 'prepaid'
                    """

        move_selection = ""
        report_info = _('')
        move_selection += ""

        query_end = ""
        if start_date:
            query_end += " AND ass.real_purchase_date >= '%s' " % str(start_date)
        if end_date:
            query_end += " AND ass.real_purchase_date <= '%s' " % str(end_date)
        if account_ids:
            query_end += " AND c.account_depreciation_id in %s " % str(
                tuple(account_ids)).replace(',)', ')')
        if branch_ids:
            query_end += " AND (ass.branch_id in %s or ass.branch_id is null)" % str(
                tuple(branch_ids)).replace(',)', ')')
        if category_ids:
            query_end += " AND ass.category_id in %s " % str(
                tuple(category_ids)).replace(',)', ')')
        reports = [report_account_prepaid]

        query_groupby = "group by b.name,ass.id,ass.code,ass.name,c.id, c.name, " \
                        "sales.name,ass.real_purchase_value, " \
                        "ass.real_purchase_date,a.code,a.name, " \
                        "ass.state,ass.method_number, aac.name, ai.number,a1.name,a2.name,a3.name,a4.name,analytic_combination, dlo.remaining_value "

        query_order = "order by branch_name"
        for report in reports:
            cr.execute(query_start + query_end + query_groupby + query_order)
            print query_start + query_end + query_groupby + query_order
            all_lines = cr.dictfetchall()
            asset_ids = []

            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': 0,
                        'branch_name': str(x['branch_name'].encode('ascii', 'ignore').decode('ascii')) if x['branch_name'] != None else '',
                        'asset_id': x['asset_id'] or 0,
                        'asset_code': str(x['asset_code'].encode('ascii', 'ignore').decode('ascii')) if x['asset_code'] != None else '',
                        'asset_name': str(x['asset_name'].encode('ascii', 'ignore').decode('ascii')) if x['asset_name'] != None else '',
                        'category_name': str(x['category_name'].encode('ascii', 'ignore').decode('ascii')) if x['category_name'] != None else '',
                        'asset_owner': str(x['asset_owner'].encode('ascii', 'ignore').decode('ascii')) if x['asset_owner'] != None else '',
                        'purchase_value': x['purchase_value'] or 0,
                        'depr_jan': x['jan'] or 0,
                        'depr_feb': x['feb'] or 0,
                        'depr_mar': x['mar'] or 0,
                        'depr_apr': x['apr'] or 0,
                        'depr_mei': x['mei'] or 0,
                        'depr_jun': x['jun'] or 0,
                        'depr_jul': x['jul'] or 0,
                        'depr_aug': x['aug'] or 0,
                        'depr_sep': x['sep'] or 0,
                        'depr_okt': x['okt'] or 0,
                        'depr_nop': x['nop'] or 0,
                        'depr_des': x['des'] or 0,
                        'depr_ttloy': x['ttloy'] or 0,
                        'purchase_date': str(x['purchase_date'].encode('ascii', 'ignore').decode('ascii')) if x['purchase_date'] != None else '',
                        'coa_depr_code': str(x['coa_depr_code'].encode('ascii', 'ignore').decode('ascii')) if x['coa_depr_code'] != None else '',
                        'coa_depr_name': str(x['coa_depr_name'].encode('ascii', 'ignore').decode('ascii')) if x['coa_depr_name'] != None else '',
                        'number_of_depr': x['number_of_depr'] or 0,
                        'depr_end_date': x['depr_end_date'] or 0,
                        'asset_account' : x['asset_account'], 
                        'nomor_sin': x['nomor_sin'],
                        'analytic_1' : x['analytic1_name'],
                        'analytic_2' : x['analytic2_name'],
                        'analytic_3' : x['analytic3_name'],
                        'analytic_4' : x['analytic4_name'],
                        'analytic_combination' : x['analytic_combination'],
                        'status': str(x['status'].encode('ascii', 'ignore').decode('ascii')) if x['status'] != None else '', 
                        'nbv': x['nbv'] or 0,
                        }, all_lines)
                report.update({'asset_ids': p_map})
        reports = filter(lambda x: x.get('asset_ids'), reports)
        if not reports:
            reports = [{'title_short': 'Laporan Prepaid', 'asset_ids':
                [{'no': 0,
                  'branch_name': 'NO DATA FOUND',
                  'asset_id': 0,
                  'asset_code': 'NO DATA FOUND',
                  'asset_name': 'NO DATA FOUND',
                  'category_name': 'NO DATA FOUND',
                  'asset_owner': 'NO DATA FOUND',
                  'purchase_value': 0,
                  'depr_jan': 0,
                  'depr_feb': 0,
                  'depr_mar': 0,
                  'depr_apr': 0,
                  'depr_mei': 0,
                  'depr_jun': 0,
                  'depr_jul': 0,
                  'depr_aug': 0,
                  'depr_sep': 0,
                  'depr_okt': 0,
                  'depr_nop': 0,
                  'depr_des': 0,
                  'depr_ttloy': 0,
                  'nbv': 0,
                  'purchase_date': 'NO DATA FOUND',
                  'coa_depr_code': 'NO DATA FOUND',
                  'coa_depr_name': 'NO DATA FOUND',
                  'number_of_depr': 0,
                  'depr_end_date': 'NO DATA FOUND',
                  'analytic_1': 'NO DATA FOUND',
                  'analytic_2': 'NO DATA FOUND',
                  'analytic_3': 'NO DATA FOUND',
                  'analytic_4': 'NO DATA FOUND',
                  'asset_account' : 'NO DATA FOUND',
                  'nomor_sin': 'NO DATA FOUND',
                  'analytic_combination': 'NO DATA FOUND',
                  'status': 'NO DATA FOUND', }], 'title': ''}]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
        ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
        })
        super(dym_report_account_prepaid_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                              grouping=True, monetary=False, dp=False,
                              currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_hutan_invoice_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)


class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_account_prepaid.report_account_prepaid'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_account_prepaid.report_account_prepaid'
    _wrapped_report_class = dym_report_account_prepaid_print
