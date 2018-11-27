from datetime import datetime, date, timedelta
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm
import decimal

class dym_report_kinerjasa_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_kinerjasa_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})


    def get_domain_wo(self, data):
        domain_wo = [('state','in',('done','open'))]
        if data['branch_ids']:
            domain_wo.append(('branch_id', 'in', data['branch_ids']))
        if data['report_type'] == 'Harian':
            domain_wo.append(('date','>=',data['start_date']))
            domain_wo.append(('date','<=',data['end_date']))
        if data['report_type'] == 'Bulanan':
            next_month = date(data['end_year'], data['end_month'], 1).replace(day=28) + timedelta(days=4)
            last_day_of_month = next_month - timedelta(days=next_month.day)
            first_day_of_month = date(data['start_year'], data['start_month'], 1)
            domain_wo.append(('date','>=',datetime.strftime(first_day_of_month, '%Y-%m-%d')))
            domain_wo.append(('date','<=',datetime.strftime(last_day_of_month, '%Y-%m-%d')))
        if data['report_type'] == 'Tahunan':
            next_month = date(data['end_year'], 12, 1).replace(day=28) + timedelta(days=4)
            last_day_of_month = next_month - timedelta(days=next_month.day)
            first_day_of_month = date(data['start_year'], 1, 1)
            domain_wo.append(('date','>=',datetime.strftime(first_day_of_month, '%Y-%m-%d')))
            domain_wo.append(('date','<=',datetime.strftime(last_day_of_month, '%Y-%m-%d')))
        return domain_wo

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context        

        query_sa_id = """
            select distinct(sa_id) sa_id from dym_work_order where sa_id is not null and state = 'done'
        """

        if data['branch_ids']:
            query_sa_id += " and branch_id in %s" % str(tuple(data['branch_ids'])).replace(',)', ')')
        else:
            user = self.pool.get('res.users').browse(cr, uid, uid)
            branch_ids = [x.id for x in user.branch_ids]
            query_sa_id += " and branch_id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        
        self.cr.execute(query_sa_id)
        all_sa = self.cr.dictfetchall()
        all_sa_ids = []
        for x in all_sa:
            all_sa_ids.append(x['sa_id'])
        sa_ids = all_sa_ids
        if data['sa_ids']:
            sa_ids = data['sa_ids']

        datas = []
        for sa_id in sa_ids:
            #ROW DAN SA
            row = {}
            sa = self.pool.get('hr.employee').browse(cr, uid, sa_id)

            #DOMAIN WO
            domain_wo = self.get_domain_wo(data)
            domain_wo.append(('sa_id', '=', sa_id))
            wo_ids = self.pool.get('dym.work.order').search(cr, uid, domain_wo)
            wo = self.pool.get('dym.work.order').browse(cr, uid, wo_ids)

            #DOMAIN WOL
            domain_wol = [('work_order_id','in', wo_ids)]
            if data['product_ids']:
                domain_wol.append(('product_id','in', data['product_ids']))
            wol_ids = self.pool.get('dym.work.order.line').search(cr, uid, domain_wol)
            wol = self.pool.get('dym.work.order.line').browse(cr, uid, wol_ids)

            sum_claim = 0
            sum_kpb = 0
            sum_quickserv = 0
            sum_lightrep = 0
            sum_heavyrep = 0
            sum_job = 0
            total = 0
            jam_terpakai = 0
            rp_jasa = 0
            rp_sparepart = 0
            rp_accessories = 0

            for wo_item in wo:
                if wo_item.type == 'CLA': sum_claim += 1
                if wo_item.type == 'KPB': sum_kpb += 1
                if wo_item.type == 'WAR': sum_job += 1

                #DOMAIN SSWO
                domain_woss = [('work_order_id','=', wo_item.id),('state_wo','=', 'finish')]
                woss_ids = self.pool.get('dym.start.stop.wo').search(cr, uid, domain_woss)
                woss = self.pool.get('dym.start.stop.wo').browse(cr, uid, woss_ids)

                for woss_item in woss:
                    before = datetime.strptime(woss_item.start, '%Y-%m-%d %H:%M:%S')
                    after  = datetime.strptime(woss_item.finish, '%Y-%m-%d %H:%M:%S')
                    jam_terpakai  += (decimal.Decimal((after - before).seconds) / 3600)


            for wol_item in wol:
                if wol_item.categ_id_2.name == 'Quick Service': sum_quickserv += 1
                if wol_item.categ_id_2.name == 'Light Repair': sum_lightrep += 1
                if wol_item.categ_id_2.name == 'Heavy Repair': sum_heavyrep += 1
                if wol_item.categ_id == 'Service': rp_jasa = rp_jasa + wol_item['price_subtotal']
                if wol_item.categ_id == 'Sparepart': rp_sparepart = rp_sparepart + wol_item['price_subtotal']
                if wol_item.categ_id_2.parent_id.name == 'ACCESSORIES': rp_accessories = rp_accessories + wol_item['price_subtotal']

            total = sum_claim + sum_kpb + sum_quickserv + sum_lightrep + sum_heavyrep + sum_job
            
            row['no'] = 0
            row['nama_sa'] = sa.name_related
            row['sum_claim'] = sum_claim
            row['sum_kpb'] = sum_kpb
            row['sum_quickserv'] = sum_quickserv
            row['sum_lightrep'] = sum_lightrep
            row['sum_heavyrep'] = sum_heavyrep
            row['sum_job'] = sum_job
            row['total'] = total
            row['jam_terpakai'] = jam_terpakai
            row['rp_jasa'] = rp_jasa
            row['rp_sparepart'] = rp_sparepart
            row['rp_accessories'] = rp_accessories
            datas.append(row)

        reports = filter(lambda x: datas, [{'datas': datas}])

        if not reports:
            reports = [{'datas': [{
                'no': 0,
                'nama_sa': 'NO DATA FOUND',
                'sum_claim': 0,
                'sum_kpb': 0,
                'sum_quickserv': 0,
                'sum_lightrep': 0,
                'sum_heavyrep': 0,
                'sum_job': 0,
                'total': 0,
                'jam_terpakai': 0,
                'rp_jasa': 0,
                'rp_sparepart': 0,
                'rp_accessories': 0
                }]}]

        self.localcontext.update({'reports': reports})
        super(dym_report_kinerjasa_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_kinerjasa_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_kinerjasa.report_kinerjasa'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_kinerjasa.report_kinerjasa'
    _wrapped_report_class = dym_report_kinerjasa_print
    