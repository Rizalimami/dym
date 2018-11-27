from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_control_bank_book_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_control_bank_book_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        branch_ids = data['branch_ids']
        period_id = data['period_id']

        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " b.id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_period = " 1=1 "
        if period_id:
            where_period = " ap.id = %s" % str(period_id[0])

        
        query_control_bank_book = """
            SELECT ap.name AS period,
                c.name AS company_name,
                b.name AS branch_name,
                a.code AS account_code,
                a.name AS account_name,
                aml.debit AS saldo_bank_book,
                aml.debit AS saldo_general_ledger,
                '' AS penjelasan
                FROM account_move_line aml
                LEFT JOIN account_period ap ON aml.period_id = ap.id
                LEFT JOIN dym_branch b ON aml.branch_id = b.id
                LEFT JOIN res_company c ON b.company_id = c.id
                LEFT JOIN account_account a ON aml.account_id = a.id
                LEFT JOIN account_account_type at ON a.user_type = at.id
        """
        query_where = "WHERE at.id = 256 AND " + where_branch_ids + " AND " + where_period
        sql_query = query_control_bank_book + query_where
        self.cr.execute(sql_query)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'period': str(x['period'].encode('ascii','ignore').decode('ascii')) if x['period'] != None else '',
                'company_name': str(x['company_name'].encode('ascii','ignore').decode('ascii')) if x['company_name'] != None else '',
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                'account_name': str(x['account_name'].encode('ascii','ignore').decode('ascii')) if x['account_name'] != None else '',
                'saldo_bank_book': x['saldo_bank_book'] if x['saldo_bank_book'] > 0 else 0.0,
                'saldo_general_ledger': x['saldo_general_ledger'] if x['saldo_general_ledger'] > 0 else 0.0,
                'penjelasan': str(x['penjelasan'].encode('ascii','ignore').decode('ascii')) if x['penjelasan'] != None else '',
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 'NO DATA FOUND',
                'period': 'NO DATA FOUND',
                'company_name': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'account_code': 'NO DATA FOUND',
                'account_name': 'NO DATA FOUND',
                'saldo_bank_book': 0,
                'saldo_general_ledger': 0,
                'penjelasan': 'NO DATA FOUND',
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_control_bank_book_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_control_bank_book_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_control_bank_book.report_control_bank_book'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_control_bank_book.report_control_bank_book'
    _wrapped_report_class = dym_report_control_bank_book_print
    