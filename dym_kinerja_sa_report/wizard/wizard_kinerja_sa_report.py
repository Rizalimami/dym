import time

import openerp
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import api, models
from datetime import datetime, date, timedelta
from lxml import etree

class dym_kinerja_sa_report(osv.osv_memory):

    _name = 'dym.kinerja.sa.report'
    _description = 'Laporan Kinerja SA'

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
        res = super(dym_kinerja_sa_report, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        branch_ids = self._get_branch_ids(cr, uid, context)
        nodes_branch = doc.xpath("//field[@name='branch_ids']")
        for node in nodes_branch :
            node.set('domain', '[("id", "in", '+ str(branch_ids)+')]')

        categ_ids = self._get_categ_ids(cr, uid, 'Sparepart', context)
        nodes_branch = doc.xpath("//field[@name='product_ids']")
        for node in nodes_branch :
            node.set('domain', '[("categ_id", "in", '+ str(categ_ids)+')]')
        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'branch_ids': fields.many2many('dym.branch', 'dym_report_sa_branch_rel', 'dym_report_sa_wizard_id','branch_id', 'Branches', copy=False),
        'sa_ids': fields.many2many('hr.employee', 'dym_report_sa_user_rel', 'dym_report_sa_wizard_id','sa_id', 'Service Advisor', copy=False),
        'product_ids': fields.many2many('product.product', 'dym_report_sa_product_rel', 'dym_report_sa_wizard_id','product_id', 'Products'),
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
        value['sa_ids'] = False
        if branchs[0][2]:
            sa_ids = self.pool.get('hr.employee').search(cr, uid, [('branch_id','in',branchs[0][2]),('job_id.service_advisor','=',True)])
            domain['sa_ids'] = [('id','in',sa_ids)]
        else:
            branch_ids = self._get_branch_ids(cr, uid, context)
            sa_ids = self.pool.get('hr.employee').search(cr, uid, [('branch_id','in',branch_ids),('job_id.service_advisor','=',True)])
            domain['sa_ids'] = [('id','in',sa_ids)]
        return  {'value':value, 'domain':domain, 'warning':warning}

    def print_report(self, cr, uid, ids, context=None):
        if context is None :
            context = {}
        data = self.read(cr, uid, ids)[0]
        return {'type': 'ir.actions.report.xml', 'report_name': 'Laporan Kinerja SA', 'datas': data}
    
    def xls_export(self, cr, uid, ids, context=None):
        return self.print_report(cr, uid, ids, context=context)

