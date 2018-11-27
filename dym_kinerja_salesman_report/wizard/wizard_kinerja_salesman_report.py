import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date, timedelta
from lxml import etree

class dym_kinerja_salesman_report(osv.osv_memory):

    _name = 'dym.kinerja.salesman.report'
    _description = 'Laporan Kinerja Salesman'

    def _get_branch_ids(self, cr, uid, context=None):
        branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
        branch_ids = [b.id for b in branch_ids_user]
        return branch_ids

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if not context:
            context = {}
        res = super(dym_kinerja_salesman_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        branch_ids = self._get_branch_ids(cr, uid, context)
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')

        categ_ids = self._get_categ_ids(cr, uid, 'Unit', context)
        nodes_branch = doc.xpath("//field[@name='product_ids']")
        for node in nodes_branch :
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_ids': fields.many2many('dym.branch', 'dym_report_salesman_branch_rel', 'dym_report_salesman_wizard_id','branch_id', 'Branches', copy=False),
        'salesman_ids': fields.many2many('hr.employee', 'dym_report_salesman_user_rel', 'dym_report_salesman_wizard_id','salesman_id', 'Salesman', copy=False),
        'product_ids': fields.many2many('product.product', 'dym_report_salesman_product_rel', 'dym_report_salesman_wizard_id','product_id', 'Products'),
        'report_type':fields.selection([('Harian','Harian'),('Bulanan','Bulanan'),('Tahunan','Tahunan')], 'Type'),
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'start_month':fields.selection([(1,'Januari'),(2,'Februari'),(3,'Maret'),(4,'April'),(5,'Mei'),(6,'Juni'),(7,'Juli'),(8,'Agustus'),(9,'September'),(10,'Oktober'),(11,'November'),(12,'Desember')], 'Start Month'),
        'start_year': fields.selection([(num, str(num)) for num in range(2010, (datetime.now().year)+1 )], 'Start Year'),
        'end_month':fields.selection([(1,'Januari'),(2,'Februari'),(3,'Maret'),(4,'April'),(5,'Mei'),(6,'Juni'),(7,'Juli'),(8,'Agustus'),(9,'September'),(10,'Oktober'),(11,'November'),(12,'Desember')], 'End Month'),
        'end_year': fields.selection([(num, str(num)) for num in range(2010, (datetime.now().year)+1 )], 'End Year'),
    }        

    _defaults = {
        'start_date':fields.date.context_today,
        'end_date':fields.date.context_today,
        'start_month':date.today().month,
        'end_month':date.today().month,
        'start_year':date.today().year,
        'end_year':date.today().year,
    }


    def onchange_branch(self, cr, uid, ids, branchs, context=None):
        value = {}
        domain = {}
        warning = {}
        value['salesman_ids'] = False
        if branchs[0][2]:
            user_ids = self.pool.get('hr.employee').search(cr, uid, [('branch_id','in',branchs[0][2])])
            domain['salesman_ids'] = [('id','in',user_ids)]
        else:
            branch_ids = self._get_branch_ids(cr, uid, context)
            user_ids = self.pool.get('hr.employee').search(cr, uid, [('branch_id','in',branch_ids)])
            domain['salesman_ids'] = [('id','in',user_ids)]
        return  {'value':value, 'domain':domain, 'warning':warning}

class kinerja_salesman_report(models.AbstractModel):
    _name = 'report.dym_kinerja_salesman_report.kinerja_salesman_report_template'

    def _get_categ_ids(self, cr, uid, categ_name, context=None):
        obj_categ = self.pool.get('product.category')
        all_categ_ids = obj_categ.search(cr, uid, [])
        categ_ids = obj_categ.get_child_ids(cr, uid, all_categ_ids, categ_name)
        return categ_ids

    def _prepare_kinerja(self, cr, uid, sale_ids, report_type, context=None):
        kinerja_salesman = {}
        for dsol in self.pool.get('dealer.sale.order.line').browse(cr, uid, sale_ids):
            dso = dsol.dealer_sale_order_line_id
            day = datetime.date(datetime.strptime(dso.date_order, '%Y-%m-%d')).day
            month = datetime.date(datetime.strptime(dso.date_order, '%Y-%m-%d')).month
            year = datetime.date(datetime.strptime(dso.date_order, '%Y-%m-%d')).year
            if len(str(month)) == 1:
                month = '0' + str(month)
            if len(str(day)) == 1:
                day = '0' + str(day)
            if report_type == 'Harian':
                periode = str(year)+'-'+str(month)+'-'+str(day)
                key = str(year)+str(month)+str(day)+str(dso.branch_id.id)+str(dso.employee_id.id)
            elif report_type == 'Bulanan':
                periode = str(month)+' / '+str(year)
                key = str(year)+str(month)+str(dso.branch_id.id)+str(dso.employee_id.id)
            elif report_type == 'Tahunan':
                periode = str(year)
                key = str(year)+str(dso.branch_id.id)+str(dso.employee_id.id)
            if key not in kinerja_salesman:
                per_sales = {}
                per_sales['periode'] = periode
                per_sales['branch_id'] = dso.branch_id
                per_sales['user_id'] = dso.employee_id
                per_sales['jumlah_sale'] = 0
                per_sales['target'] = 0
                if dso.employee_id:
                    if report_type == 'Bulanan':
                        per_sales['target'] = dso.employee_id.wo_target
                    elif report_type == 'Tahunan':
                        per_sales['target'] = dso.employee_id.wo_target * 12 #tahunan
                per_sales['percentage'] = '0%'
                per_sales['rp_sale'] = 0
                per_sales['per_category'] = {}
                kinerja_salesman[key] = per_sales
            per_category = {}
            per_category['category'] = dsol.product_id.category_product_id.name
            per_category['category_sale'] = dsol.product_qty
            per_category['category_rp_sale'] = dsol.price_subtotal
            if dsol.product_id.category_product_id.id not in kinerja_salesman[key]['per_category']:
                kinerja_salesman[key]['per_category'][dsol.product_id.category_product_id.id] = per_category
            else:
                kinerja_salesman[key]['per_category'][dsol.product_id.category_product_id.id]['category_sale'] += per_category['category_sale']
                kinerja_salesman[key]['per_category'][dsol.product_id.category_product_id.id]['category_rp_sale'] += per_category['category_rp_sale']
            kinerja_salesman[key]['jumlah_sale'] += per_category['category_sale']
            kinerja_salesman[key]['rp_sale'] += per_category['category_rp_sale']
            if kinerja_salesman[key]['target'] > 0:
                kinerja_salesman[key]['percentage'] = str(kinerja_salesman[key]['jumlah_sale'] / kinerja_salesman[key]['target'])+'%'
            else:
                kinerja_salesman[key]['percentage'] = '-'
        # sorted_kinerja_salesman = {}
        # for key in sorted(kinerja_salesman):
        #     sorted_kinerja_salesman[key] = kinerja_salesman[key]
        # return sorted_kinerja_salesman
        return kinerja_salesman

    def render_html(self, cr, uid, ids, data=None, context=None):
        registry = openerp.registry(cr.dbname)
        report_type = False
        start_date = False
        end_date = False
        start_month = False
        end_month = False
        start_year = False
        end_year = False
        branch_ids = []
        product_ids = []
        user_ids = []
        domain = [('dealer_sale_order_line_id.state','=','done')]

        check_wizard = registry.get('dym.kinerja.salesman.report').read(cr, uid, ids, context=context)
        if check_wizard:
            data_wizard = check_wizard[0]
            if data_wizard['product_ids']:
                product_ids = data_wizard['product_ids']
            else:
                categ_ids = self._get_categ_ids(cr, uid, 'Unit', context)
                product_ids = self.pool.get('product.product').search(cr, uid, [('categ_id','in',categ_ids)])
            domain.append(('product_id', 'in', product_ids))

            if data_wizard['branch_ids']:
                branch_ids =  data_wizard['branch_ids']
            else:
                branch_ids_user = self.pool.get('res.users').browse(cr, uid, uid).branch_ids
                branch_ids = [b.id for b in branch_ids_user]
            domain.append(('dealer_sale_order_line_id.branch_id', 'in', branch_ids))

            if data_wizard['salesman_ids']:
                user_ids = data_wizard['salesman_ids']
            else:
                user_ids = self.pool.get('hr.employee').search(cr, uid, [('branch_id','in',branch_ids)])
            domain.append(('dealer_sale_order_line_id.employee_id', 'in', user_ids))

            report_type = data_wizard['report_type']
            start_date = data_wizard['start_date']
            end_date = data_wizard['end_date']
            start_month = data_wizard['start_month']
            end_month = data_wizard['end_month']
            start_year = data_wizard['start_year']
            end_year = data_wizard['end_year']

            sale_ids = []
            if report_type == 'Harian':
                if start_date > end_date:
                    raise osv.except_osv(('Perhatian !'), ("Tanggal Awal harus lebih kecil dari tanggal akhir!."))
                domain += [('dealer_sale_order_line_id.date_order','>=',start_date),('dealer_sale_order_line_id.date_order','<=',end_date)]
                sale_ids = registry.get('dealer.sale.order.line').search(cr, uid, domain, context=None)
            elif report_type == 'Bulanan':
                next_month = date(end_year, end_month, 1).replace(day=28) + timedelta(days=4)
                last_day_of_month = next_month - timedelta(days=next_month.day)
                first_day_of_month = date(start_year, start_month, 1)
                if first_day_of_month > last_day_of_month:
                    raise osv.except_osv(('Perhatian !'), ("Periode Awal harus lebih kecil dari periode akhir!."))

                domain += [('dealer_sale_order_line_id.date_order','>=',datetime.strftime(first_day_of_month, '%Y-%m-%d')),('dealer_sale_order_line_id.date_order','<=',datetime.strftime(last_day_of_month, '%Y-%m-%d'))]
                sale_ids = registry.get('dealer.sale.order.line').search(cr, uid, domain, context=None)
            elif report_type == 'Tahunan':
                if start_year > end_year:
                    raise osv.except_osv(('Perhatian !'), ("Tahun Awal harus lebih kecil dari tahun akhir!."))
                last_day_of_month = date(end_year, 12, 1)
                first_day_of_month = date(start_year, 1, 1)
                domain += [('dealer_sale_order_line_id.date_order','>=',datetime.strftime(first_day_of_month, '%Y-%m-%d')),('dealer_sale_order_line_id.date_order','<=',datetime.strftime(last_day_of_month, '%Y-%m-%d'))]
                sale_ids = registry.get('dealer.sale.order.line').search(cr, uid, domain, context=None)

            kinerja_salesman = self._prepare_kinerja(cr, uid, sale_ids, report_type)
            if not kinerja_salesman:
                raise osv.except_osv(('Perhatian !'), ("Transaksi tidak ditemukan!."))
        report_obj = self.pool['report']
        report = report_obj._get_report_from_name(cr, uid, 'dym_kinerja_salesman_report.kinerja_salesman_report_template')
        docargs = {'doc_ids': ids,'doc_model': report.model,'docs': data,'report_type': report_type,'start_date': start_date,'end_date': end_date,'start_month': start_month,'end_month': end_month,'start_year': start_year,'end_year': end_year,'kinerja_salesman': kinerja_salesman}
        return report_obj.render(cr, uid, ids, 'dym_kinerja_salesman_report.kinerja_salesman_report_template', docargs, context=context)