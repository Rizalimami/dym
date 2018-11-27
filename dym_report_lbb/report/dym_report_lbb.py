from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_lbb_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_lbb_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def get_perpc(self, categ):
        cr = self.cr
        uid = self.uid
        context = self.context 

        pc_domain = [('parent_id.parent_id.name','=', categ)]
        pc_ids = self.pool.get('product.category').search(cr, uid, pc_domain)
        pc = self.pool.get('product.category').browse(cr, uid, pc_ids)
        datas = []
        for pc_item in pc:

            kpb_1 = 0
            kpb_2 = 0
            kpb_3 = 0
            kpb_4 = 0
            kpb_5 = 0
            claim = 0
            jr = 0
            qs_cs = 0
            qs_ls = 0
            qs_or = 0
            lr = 0
            hr = 0

            wo_domain = [('product_id.categ_id','=', pc_item.id)]
            wo_ids = self.pool.get('dym.work.order').search(cr, uid, wo_domain)
            wo = self.pool.get('dym.work.order').browse(cr, uid, wo_ids)

            wol_domain = [('work_order_id','in', wo_ids)]
            wol_ids = self.pool.get('dym.work.order.line').search(cr, uid, wol_domain)
            wol = self.pool.get('dym.work.order.line').browse(cr, uid, wol_ids)

            for wo_item in wo:
                if wo_item.type == 'KPB' and wo_item.kpb_ke == '1' : kpb_1 += 1
                if wo_item.type == 'KPB' and wo_item.kpb_ke == '2' : kpb_2 += 1
                if wo_item.type == 'KPB' and wo_item.kpb_ke == '3' : kpb_3 += 1
                if wo_item.type == 'KPB' and wo_item.kpb_ke == '4' : kpb_4 += 1
                if wo_item.type == 'CLA' : claim += 1
                if wo_item.type == 'WAR' : jr += 1

            for wol_item in wol:
                if wol_item.categ_id_2.name == 'Quick Service' and wol_item.product_id.name == 'SERVICE LENGKAP' : qs_cs += 1
                if wol_item.categ_id_2.name == 'Quick Service' and wol_item.product_id.name == 'SERVICE RINGAN': qs_ls += 1
                if wol_item.categ_id_2.name == 'Quick Service' and wol_item.product_id.name == 'OR+': qs_or += 1
                if wol_item.categ_id_2.name == 'Light Repair': lr += 1
                if wol_item.categ_id_2.name == 'Heavy Repair': hr += 1

            row = {}
            row['no'] = 0
            row['type'] = pc_item.name
            row['total_unit_entry'] = 0
            row['kpb_1'] = kpb_1
            row['kpb_2'] = kpb_2
            row['kpb_3'] = kpb_3
            row['kpb_4'] = kpb_4
            row['kpb_5'] = kpb_5
            row['claim'] = claim
            row['qs_cs'] = qs_cs
            row['qs_ls'] = qs_ls
            row['qs_or'] = qs_or
            row['lr'] = lr
            row['hr'] = hr
            row['total'] = 0
            row['jr'] = jr
            row['member_card'] = 0
            row['drive_thru'] = 0
            row['unit_safety'] = 0

            datas.append(row)

        return datas

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        

        datas_cub = self.get_perpc('Cub')
        datas_matic = self.get_perpc('Matic')
        datas_sport = self.get_perpc('Sport')

        reports = [
                {'datas_cub': datas_cub},
                {'datas_matic': datas_matic},
                {'datas_sport': datas_sport}
            ]

        if not reports:
            raise osv.except_osv(('Warning'), ('Data Report Tidak Ditemukan !'))
        
        self.localcontext.update({'reports': reports})
        super(dym_report_lbb_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_lbb_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_lbb.report_lbb'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_lbb.report_lbb'
    _wrapped_report_class = dym_report_lbb_print
    