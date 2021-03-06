import time
import pytz
#import serial.tools
from openerp import SUPERUSER_ID
from datetime import datetime
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from openerp import netsvc
from openerp import pooler
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.osv.orm import browse_record, browse_null
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from openerp.osv import osv, fields
from datetime import datetime, timedelta


class dym_location(osv.osv):
    _inherit = 'stock.location'
    
    def _onchange_province(self, cr, uid, ids, state_id):
        if state_id:
            return {
                    'domain' : {
                                'city_id':[('state_id','=',state_id)],
                                },
                    'value' : {
                               'city_id':False,
                               }
                    }
        else:
            return {
                    'domain' : {
                                'city_id':[('state_id','=',False)],
                                },
                    'value' : {
                               'city_id':False,
                               }
                    }
        return True
    
    def _onchange_city(self, cr, uid, ids, city_id):
        if city_id:
            return {
                    'domain' : {
                                'kecamatan_id':[('city_id','=',city_id)],
                                },
                    'value' : {
                               'kecamatan_id':False,
                               }
                    }
        else:
            return {
                    'domain' : {
                                'kecamatan_id':[('city_id','=',False)],
                                },
                    'value' : {
                               'kecamatan_id':False,
                               }
                    }
        return True
            
    def _onchange_kecamatan(self, cr, uid, ids, kecamatan_id):
        if kecamatan_id:
            kec = self.pool.get("dym.kecamatan").browse(cr, uid, kecamatan_id)
            return {
                    'domain' : {
                                'zip_id':[('kecamatan_id','=',kecamatan_id)],
                                },
                    'value' : {
                               'kecamatan':kec.name,
                               'zip_id':False,
                               }
                    }
        else:
            return {
                    'domain' : {
                                'zip_id':[('kecamatan_id','=',False)],
                                },
                    'value' : {
                               'kecamatan':False,
                               'zip_id':False,
                               }
                    }
        return True
    
    def _onchange_zip(self, cr, uid, ids, zip_id):
        if zip_id:
            kel = self.pool.get("dym.kelurahan").browse(cr, uid, zip_id)
            return {
                    'value' : {
                              'kelurahan':kel.name,
                              }
                    }
        else:
            return {
                    'value' : {
                               'kelurahan':False,
                               }
                    }
        return True
    
    _columns = {
                'start_date':fields.date('start date'),
                'end_date':fields.date('end date'),
                'maximum_qty': fields.integer('Maximum Qty'),  
                'street':fields.char('Address'),
                'street2': fields.char(),
                'rt':fields.char('rt',size = 3),
                'rw':fields.char('rw',size = 3),
                'kelurahan':fields.char('Kelurahan',size = 100),
                'kecamatan_id':fields.many2one('dym.kecamatan','Kecamatan'),
                'kecamatan':fields.char('Kecamatan', size=100),
                'city_id':fields.many2one('dym.city','City'),
                'state_id':fields.many2one('res.country.state','Province'),
                'zip_id':fields.many2one('dym.kelurahan','ZIP Code'),
                'usage':fields.selection([
                        ('supplier', 'Supplier Location'),
                        ('view', 'View'),
                        ('nrfs', 'Not Ready For Sale'),
                        ('kpb', 'KPB'),
                        ('asset_clearing', 'Asset Clearing'),
                        ('internal', 'Internal Location'),
                        ('customer', 'Customer Location'),
                        ('inventory', 'Inventory'),
                        ('procurement', 'Procurement'),
                        ('production', 'Production'),
                        ('transit', 'Transit Location')],
                'Location Type', required=True,
                help="""* Supplier Location: Virtual location representing the source location for products coming from your suppliers
                       \n* View: Virtual location used to create a hierarchical structures for your warehouse, aggregating its child locations ; can't directly contain products
                       \n* Internal Location: Physical locations inside your own warehouses,
                       \n* Customer Location: Virtual location representing the destination location for products sent to your customers
                       \n* Inventory: Virtual location serving as counterpart for inventory operations used to correct stock levels (Physical inventories)
                       \n* Procurement: Virtual location serving as temporary counterpart for procurement operations when the source (supplier or production) is not known yet. This location should be empty when the procurement scheduler has finished running.
                       \n* Production: Virtual counterpart location for production operations: this location consumes the raw material and produces finished products
                       \n* Transit Location: Counterpart location that should be used in inter-companies or inter-warehouses operations
                      """, select=True),
                'jarak': fields.char('Jarak'),
                'biaya': fields.float('Biaya'),
                'beban': fields.char('Beban'),
                'target': fields.integer('Target'),
                }
        
    _defaults = {
                'start_date': fields.date.context_today,
                'end_date': fields.date.context_today,
                }
    
class dym_stock_location(osv.osv):
    _inherit = 'stock.location'
    
    def _get_current_stock(self, cr, uid, ids, name, args, context=None):
        res = {}
        for location in self.browse(cr, uid, ids, context=context):
            res[location.id] = 0.00
            quants_ids = self.pool.get('stock.quant').search(cr,uid,[('location_id','=',location.id)])
            if quants_ids:
                quants = self.pool.get('stock.quant').browse(cr,uid,quants_ids)
                for quant in quants:
                    res[location.id] += quant.qty
        return res 

    def _quantity_available(self, cr, uid, ids, name, args, context=None):
        res = {}
        for location in self.browse(cr, uid, ids, context=context):
            res[location.id] = 0.00
            quants_ids = self.pool.get('stock.quant').search(cr,uid,[('location_id','=',location.id),('reservation_id','=',False)])
            if quants_ids:
                quants = self.pool.get('stock.quant').browse(cr,uid,quants_ids)
                for quant in quants:
                    res[location.id] += quant.qty
        return res

    def _get_default_branch(self,cr,uid,ids,context=None):
        user_obj = self.pool.get('res.users')        
        user_browse = user_obj.browse(cr,uid,uid)
        branch_ids = False
        branch_ids = user_browse.branch_ids and len(user_browse.branch_ids) == 1 and user_browse.branch_ids[0].id or False                
        return branch_ids 
        
    def _get_branch(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for location in self.browse(cr, uid, ids, context=context):
            res[location.id] = location.sudo().warehouse_id.branch_id.id            
        return res

    def _get_warehouse(self, cr, uid, ids, context=None):
        location_ids = self.pool.get('stock.location').search(cr, uid, [('warehouse_id','in',ids)])
        return list(set(location_ids))

    _columns = {
                'branch_id': fields.function(_get_branch, type='many2one', relation='dym.branch', string='Branch',
                    store={
                        'stock.location': (lambda self, cr, uid, ids, c={}: ids, ['warehouse_id'], 10),
                        'stock.warehouse': (_get_warehouse, ['branch_id'], 10),
                    }, help="Branch."),
                'description':fields.char('Description'),
                'jenis': fields.selection([('umum','Umum'),('canvasing','Canvasing'),('channel','Channel'),('gudang','Gudang'),('pameran','Pameran'),('pos','POS'),('showroom','Showroom'),('part','Part')], 'Jenis'),
                'quantity_on_hand': fields.function(_get_current_stock, string='Quantity On Hand'),
                'quantity_available': fields.function(_quantity_available, string='Quantity Available'),
                }    

    _defaults = {
        # 'branch_id': _get_default_branch,
    }    
  
    
    
    