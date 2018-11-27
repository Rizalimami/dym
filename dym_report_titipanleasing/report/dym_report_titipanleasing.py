from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_titipanleasing_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_titipanleasing_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        
        query_titipanleasing = """
            select b.branch_status branch_status,
            b.name cabang,
            av.division divisi,
            rp.name nama_leasing,
            acl.name ket,
            ac.name payment_method,
            av.date tanggal,
            av.number no_cde,
            av.paid_amount nilai_titipan,
            dat.date alokasi_tgl,
            dat.name alokasi_no,
            av.id no_cde_id,
            av.move_id
            from account_voucher av
            left join account_voucher_line acl on acl.voucher_id = av.id
            left join dym_branch b on av.branch_id = b.id 
            left join res_partner rp on av.partner_id = rp.id 
            left join account_journal ac on av.journal_id = ac.id
            left join dym_alokasi_titipan dat on dat.voucher_id = av.id
            where av.number like 'CDE%' and rp.finance_company = true
        """

        query_where = ""
        if data['start_date']:
            query_where += " and av.date >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and av.date <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and av.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')


        print query_titipanleasing + query_where
        self.cr.execute(query_titipanleasing + query_where)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'branch_status': x['branch_status'],
                'cabang': x['cabang'],
                'divisi': x['divisi'],
                'nama_leasing': x['nama_leasing'],
                'ket': x['ket'],
                'payment_method': x['payment_method'],
                'tanggal': x['tanggal'],
                'no_cde': x['no_cde'],
                'nilai_titipan': x['nilai_titipan'],
                'alokasi_tanggal': x['alokasi_tgl'],
                'alokasi_no': x['alokasi_no'],
                'cpa_no': '',
                'nilai_alokasi': 0,
                'sisa_titipan': 0,
                'a_code': '',
                'a_name': '',
                'aa_combi': '',
                'aa_company': '',
                'aa_bisnisunit': '',
                'aa_branch': '',
                'aa_costcenter': '',
                'no_cde_id': x['no_cde_id'],
                'move_id': x['move_id'],
                }, all_lines)

            for p in datas:
               av_account = self.pool.get('account.voucher').browse(cr, uid, p['no_cde_id'])
               p.update({'a_code': av_account.account_id.code})
               p.update({'a_name': av_account.account_id.name})
               p.update({'aa_combi': "%s/%s/%s/%s" % (av_account.analytic_1.code,av_account.analytic_2.code,av_account.analytic_3.code,av_account.analytic_4.code) })
               p.update({'aa_company': av_account.analytic_1.name})
               p.update({'aa_bisnisunit': av_account.analytic_2.name})
               p.update({'aa_branch': av_account.analytic_3.name})
               p.update({'aa_costcenter': av_account.analytic_4.name})

               if p['alokasi_no']:
                    dat_domain = [('name','=', p['alokasi_no'])]
                    dat_ids = self.pool.get('dym.alokasi.titipan').search(cr, uid, dat_domain)
                    dat = self.pool.get('dym.alokasi.titipan').browse(cr, uid, dat_ids)
                    p.update({'nilai_alokasi': dat.total_alokasi})
               else:
                    ml_domain = [('move_id','=', p['move_id'])]
                    ml_ids = self.pool.get('account.move.line').search(cr, uid, ml_domain)
                    avl_domain = [('move_line_id','in', ml_ids)]
                    avl_ids = self.pool.get('account.voucher.line').search(cr, uid, avl_domain)
                    avl = self.pool.get('account.voucher.line').browse(cr, uid, avl_ids)
                    p.update({'nilai_alokasi': abs(avl.voucher_id.amount)})
                    p.update({'cpa_no': avl.voucher_id.number})
                    p.update({'alokasi_tanggal': avl.voucher_id.date})
               p.update({'sisa_titipan': p['nilai_titipan']-p['nilai_alokasi']})

            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            raise osv.except_osv(('Warning'), ('Data Tidak Ditemukan !'))
        
        self.localcontext.update({'reports': reports})
        super(dym_report_titipanleasing_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_titipanleasing_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_titipanleasing.report_titipanleasing'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_titipanleasing.report_titipanleasing'
    _wrapped_report_class = dym_report_titipanleasing_print
    