from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_registerpraso_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_registerpraso_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        
        
        query_registerpraso = """
            select reg.name no_reg, 
            b.name branch, 
            hr.name_related salesman, 
            pso.name no_pso, 
            dso.name no_dso, 
            case 
             when pso.state='draft' then 'Draft'
             when pso.state='progress' then 'Memo'
             when pso.state='so' then 'Sales Memo'
             when pso.state='done' then 'Done'
             when pso.state='cancelled' then 'Cancelled'
            end state,
            reg.tanggal_distribusi tgl_distribusi,
            (pso.date_order - reg.tanggal_distribusi) as aging
            from dealer_spk pso
            left join dealer_sale_order dso on dso.dealer_spk_id = pso.id
            left join dealer_register_spk_line reg on pso.register_spk_id = reg.id
            left join dym_branch b on pso.branch_id = b.id
            left join hr_employee hr on pso.employee_id = hr.id
        """

        query_where = " where 1=1"
        if data['start_date']:
            query_where += " and pso.date_order >= '%s'" % str(data['start_date'])
        if data['end_date']:
            query_where += " and pso.date_order <= '%s'" % str(data['end_date'])
        if data['branch_ids']:
            query_where += " and pso.branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')

        self.cr.execute(query_registerpraso + query_where)
        all_lines = self.cr.dictfetchall()

        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'no': 0,
                'no_reg' : x['no_reg'],
                'branch' : x['branch'],
                'salesman' : x['salesman'],
                'no_pso' : x['no_pso'],
                'no_dso' : x['no_dso'],
                'state' : x['state'],
                'tgl_distribusi': x['tgl_distribusi'],
                'aging': x['aging']
                }, all_lines)
            reports = filter(lambda x: datas, [{'datas': datas}])
        else :
            reports = [{'datas': [{
                'no': 0,
                'no_reg' : 'DATA NOT FOUND',
                'branch' : 'DATA NOT FOUND',
                'salesman' : 'DATA NOT FOUND',
                'no_pso' : 'DATA NOT FOUND',
                'no_dso' : 'DATA NOT FOUND',
                'state' : 'DATA NOT FOUND',
                'tgl_distribusi': 'DATA NOT FOUND',
                'aging': 0
                }]}]
        
        self.localcontext.update({'reports': reports})
        super(dym_report_registerpraso_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_registerpraso_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_registerpraso.report_registerpraso'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_registerpraso.report_registerpraso'
    _wrapped_report_class = dym_report_registerpraso_print
    