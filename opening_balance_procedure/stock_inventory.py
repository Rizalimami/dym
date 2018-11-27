# -*- encoding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
from psycopg2 import IntegrityError, OperationalError, errorcodes
from openerp import netsvc, SUPERUSER_ID
import openerp.pooler as pooler
import openerp.sql_db as sql_db
import json
from datetime import datetime
import logging
import base64
import uuid
import time
import pdb
_logger = logging.getLogger(__name__)

class stock_inventory(osv.osv):
    _inherit = "stock.inventory"

    def _get_analytic_2(self, cr, uid, ids, context=None):
        for x in ids.parent_id:
            if x.segmen == 2 :
                return [x.id]
            else:
                return self._get_analytic_2(cr, uid, x, context=None)

    def insert_many(self, cr, uid, table, id_column, values, context=None):
        if not values:
            return []

        keys = values[0].keys()
        query = cr.mogrify("INSERT INTO {} ({}) VALUES {} RETURNING {}".format(
                table,
                ', '.join(keys),
                ', '.join(['%s'] * len(values)),
                id_column
            ), [tuple(v.values()) for v in values])

        cr.execute(query)
        return cr.fetchall()

    def bulk_stock_inventory(self, cr, uid, data, context=None):
        result = []
        stock_inventory = []
        stock_inventory_line = []
        stock_quant = []
        stock_move = []
        product_price_branch = []
        product_price_history = []
        account_move = []
        account_move_lines = []
        # wkf_instances = []
        # wf_service = netsvc.LocalService("workflow")

        # INSERT HEADER STOCK INVENTORY
        start_time = datetime.now()
        begin_time = start_time
        stock_vals = []
        for n,dt in enumerate(data,start=0):
            if 'Company' in dt and not dt['Company']:
                continue
            module_analytic = dt['Analytical Account'].split('.',1)[0]
            identifier_analytic = dt['Analytical Account'].split('.',1)[1]
            module_location = dt['Header Location'].split('.',1)[0]
            identifier_location = dt['Header Location'].split('.',1)[1]
            module_warehouse = dt['Warehouse'].split('.',1)[0]
            identifier_warehouse = dt['Warehouse'].split('.',1)[1]
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
            company_id = int(cr.fetchone()[0])

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_warehouse, identifier_warehouse))
            warehouse_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
            period_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_account WHERE name = 'AP Suspense' AND  company_id = %s """, ((company_id,)))
            income_account = cr.fetchone()
            loss_account = income_account

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
            analytic_4 = cr.fetchone()

            cr.execute("""SELECT parent_id FROM account_analytic_account WHERE   id = %s """, (analytic_4))
            analytic_3 = cr.fetchone()

            analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, [analytic_3[0]], context=None)
            analytic_2 = self._get_analytic_2(cr, uid, analytic_3, context=None)
            
            cr.execute("""SELECT id FROM account_analytic_account WHERE   segmen = 1 AND company_id = %s """, ((int(company_id),)))
            analytic_1 = cr.fetchone()

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_location, identifier_location))
            location = cr.fetchone()

            values = {
                "create_uid" : 1,
                "create_date" : datetime.now().strftime('%Y-%m-%d'),
                "write_date" : datetime.now().strftime('%Y-%m-%d'),
                "write_uid" : 1,
                "location_id" : location[0],
                "warehouse_id" : warehouse_id,
                "company_id" : company_id,
                "period_id" : period_id,
                "date" : dt['Date'],
                "name" : dt['Inventory Reference'],
                "filter" : 'partial',
                "analytic_1" : analytic_1[0],
                "analytic_2" : analytic_2[0],
                "analytic_3" : analytic_3.id,
                "analytic_4" : analytic_4[0],
                "state" : 'confirm',
                "income_account" : income_account[0],
                "loss_account" : loss_account[0],
                "division" : dt['Division'],
                "branch_destination_id": dt['BranchDestination'],
            }
            stock_vals.append(values)

        inventory_ids = self.insert_many(cr, uid, 'stock_inventory', 'id', stock_vals, context=None)        

        finish_time = datetime.now()
        msg = 'Duration to insert %s of stock inventory = %s' % ('1', format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT STOCK INVENTORY LINE
        start_time = datetime.now()
        stock_line_vals = []
        for n,dt in enumerate(data,start=0):
            if 'Serial Number' in dt and dt['Serial Number']:
                module_serial = dt['Serial Number'].split('.',1)[0]
                identifier_serial = dt['Serial Number'].split('.',1)[1]
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_serial, identifier_serial))
                serial = cr.fetchone()[0]
            else:
                serial = None
            module_location = dt['Location'].split('.',1)[0]
            identifier_location = dt['Location'].split('.',1)[1]
            module_product = dt['Product'].split('.',1)[0]
            identifier_product = dt['Product'].split('.',1)[1]

            if 'Attribute Value' in dt and dt['Attribute Value']:
                module_attribute_value = dt['Attribute Value'].split('.',1)[0]
                identifier_attribute_value = dt['Attribute Value'].split('.',1)[1]
 
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_attribute_value, identifier_attribute_value))
                attribute_value_id = cr.fetchone()

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_location, identifier_location))
            location = cr.fetchone()
 
            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_product, identifier_product))
            product_id = cr.fetchone()
 
            values = {
                "create_uid" : 1,
                "create_date" : datetime.now(),
                "write_date" : datetime.now(),
                "write_uid" : 1,
                "location_id" : location[0],
                "prod_lot_id" : serial,
                "theoretical_qty" : 0,
                "adjustment_qty" : float(dt['Adjustment Quantity']),
                "product_qty" : float(dt['Checked Quantity']),
                "cost_price" : float(dt['Cost Price']),
                "product_id" : product_id,
                "product_uom_id" : dt['UoM'],
                "inventory_id" : inventory_ids[0],
            }
            stock_line_vals.append(values)

        inventory_line_ids = self.insert_many(cr, uid, 'stock_inventory_line', 'id', stock_line_vals, context=None)        

        result = {}
        return json.dumps({'status':'OK','message':result})
