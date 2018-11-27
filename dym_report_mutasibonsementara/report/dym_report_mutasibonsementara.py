from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_mutasibonsementara_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_mutasibonsementara_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        
        query_mutasibonsementara = """
            select ap.date bs_tgl,
            p.name karyawan,
            ap.division dept,
            ap.name bs_nama,
            ap.amount bs_nilai,
            ap.description bs_ket,
            sp.date sp_date,
            sp.name sp_name,
            sp.amount_total sp_nilai,
            sp.amount_gap sp_saldobs,
            aa1.code || '/' || aa2.code || '/' || aa3.code || '/' || aa4.code aa_combi,
            aa1.name aa_company,
            aa2.name aa_bisnisunit,
            aa3.name aa_branch,
            aa4.name aa_costcenter
            from dym_advance_payment ap
            left join dym_settlement sp on sp.advance_payment_id = ap.id
            left join dym_settlement_line spl on spl.settlement_id = sp.id
            left join res_partner p on ap.user_id = p.id
            left join account_analytic_account aa1 on spl.analytic_1 = aa1.id
            left join account_analytic_account aa2 on spl.analytic_2 = aa2.id
            left join account_analytic_account aa3 on spl.analytic_3 = aa3.id
            left join account_analytic_account aa4 on spl.analytic_account_id = aa4.id
        """

        query_where = " where 1=1 "
        if data['start_date']:
            query_where += " and ap.date >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and ap.date <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and ap.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')

        self.cr.execute(query_mutasibonsementara + query_where)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no' : 0,
                'bs_tgl' : x['bs_tgl'],
                'karyawan' : x['karyawan'],
                'dept' : x['dept'],
                'bs_nama' : x['bs_nama'],
                'bs_nilai' : x['bs_nilai'],
                'bs_ket' : x['bs_ket'],
                'sp_date' : x['sp_date'],
                'sp_name' : x['sp_name'],
                'sp_nilai' : x['sp_nilai'],
                'sp_saldobs' : x['sp_saldobs'],
                'current' : 0,
                'overdue1_7' : '',
                'overdue8_30' : '',
                'overdue31_60' : '',
                'overdue61_90' : '',
                'overdue90' : '',
                'aa_combi' : x['aa_combi'],
                'aa_company' : x['aa_company'],
                'aa_bisnisunit' : x['aa_bisnisunit'],
                'aa_branch' : x['aa_branch'],
                'aa_costcenter' : x['aa_costcenter']
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            raise osv.except_osv(('Warning'), ('Data Report Tidak Ditemukan!'))
        
        self.localcontext.update({'reports': reports})
        super(dym_report_mutasibonsementara_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_mutasibonsementara_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_mutasibonsementara.report_mutasibonsementara'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_mutasibonsementara.report_mutasibonsementara'
    _wrapped_report_class = dym_report_mutasibonsementara_print
    