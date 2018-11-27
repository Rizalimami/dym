import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date, timedelta
from lxml import etree
import decimal


class kinerja_mekanik_report(models.AbstractModel):
    _name = 'report.dym_kinerja_mekanik_report.kinerja_mekanik_report_template'

    def get_domain_wo(self, data):
        domain_wo = [('state','=','done')]
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

    def get_kinerja_mekanik_report(self, cr, uid, data, context=None):
        query_mekanik_id = """
            select distinct(mekanik_id) mekanik_id from dym_work_order where mekanik_id is not null and state = 'done'
        """
        
        cr.execute(query_mekanik_id)
        all_mekanik = cr.dictfetchall()
        all_mekanik_ids = []
        for x in all_mekanik:
            all_mekanik_ids.append(x['mekanik_id'])
        mekanik_ids = all_mekanik_ids
        if data['mekanik_ids']:
            mekanik_ids = data['mekanik_ids']

        datas = []
        for mekanik_id in mekanik_ids:
            #ROW DAN MEKANIK
            row = {}
            mekanik = self.pool.get('hr.employee').browse(cr, uid, mekanik_id)

            #DOMAIN WO
            domain_wo = self.get_domain_wo(data)
            domain_wo.append(('mekanik_id', '=', mekanik_id))
            wo_ids = self.pool.get('dym.work.order').search(cr, uid, domain_wo)
            wo = self.pool.get('dym.work.order').browse(cr, uid, wo_ids)

            #DOMAIN WOL
            domain_wol = [('work_order_id','in', wo_ids)]
            if data['product_ids']:
                domain_wol.append(('product_id','in', data['product_ids']))
            wol_ids = self.pool.get('dym.work.order.line').search(cr, uid, domain_wol)
            wol = self.pool.get('dym.work.order.line').browse(cr, uid, wol_ids)

            #DOMAIN SSWO
            domain_woss = [('mekanik_id','=', mekanik_id),('state_wo','=', 'finish')]
            woss_ids = self.pool.get('dym.start.stop.wo').search(cr, uid, domain_woss)
            woss = self.pool.get('dym.start.stop.wo').browse(cr, uid, woss_ids)

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

            for wo_item in wo:
                if wo_item.type == 'CLA': sum_claim += 1
                if wo_item.type == 'KPB': sum_kpb += 1
                if wo_item.type == 'WAR': sum_job += 1

            for wol_item in wol:
                if wol_item.categ_id_2.name == 'Quick Service': sum_quickserv += 1
                if wol_item.categ_id_2.name == 'Light Repair': sum_lightrep += 1
                if wol_item.categ_id_2.name == 'Heavy Repair': sum_heavyrep += 1
                if wol_item['categ_id'] == 'Service': rp_jasa = rp_jasa + wol_item['price_subtotal']
                if wol_item['categ_id'] == 'Sparepart': rp_sparepart = rp_sparepart + wol_item['price_subtotal']

            for woss_item in woss:
                before = datetime.strptime(woss_item.start, '%Y-%m-%d %H:%M:%S')
                after  = datetime.strptime(woss_item.finish, '%Y-%m-%d %H:%M:%S')
                jam_terpakai  += (decimal.Decimal((after - before).seconds) / 3600)

            total = sum_claim + sum_kpb + sum_quickserv + sum_lightrep + sum_heavyrep + sum_job
            
            row['no'] = 0
            row['nama_mekanik'] = mekanik.name_related
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
            datas.append(row)

        reports = filter(lambda x: datas, [{'datas': datas}])

        if not reports:
            reports = [{'datas': [{
                'no': 0,
                'nama_mekanik': 'NO DATA FOUND',
                'sum_claim': 0,
                'sum_kpb': 0,
                'sum_quickserv': 0,
                'sum_lightrep': 0,
                'sum_heavyrep': 0,
                'sum_job': 0,
                'total': 0,
                'jam_terpakai': 0,
                'rp_jasa': 0,
                'rp_sparepart': 0
                }]}]

        return reports

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        check_wizard = registry.get('dym.kinerja.mekanik.report').read(cr, uid, ids, context=context)

        if check_wizard:
            data = check_wizard[0]
            kinerja_mekanik = self.get_kinerja_mekanik_report(cr, uid, data)
            print kinerja_mekanik
            if not kinerja_mekanik:
                raise osv.except_osv(('Perhatian !'), ("Transaksi tidak ditemukan!."))

        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_kinerja_mekanik_report.kinerja_mekanik_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data, 'kinerja_mekanik': kinerja_mekanik}
        return report_obj.render(cr, uid, ids, 'dym_kinerja_mekanik_report.kinerja_mekanik_report_template', docargs, context=context)