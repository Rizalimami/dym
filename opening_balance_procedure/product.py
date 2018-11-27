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

class product_template(osv.osv):
    _inherit = "product.template"

    def bulk_product(self, cr, uid, data, context=None):
	result = []
        product_template = []
        product_product = []
        ir_model_data = []
#	pdb.set_trace()
        # INSERT PRODUCT TEMPLATE
        start_time = datetime.now()
        begin_time = start_time
        for dt in data:
            module_external_id = dt['External ID'].split('.',1)[0]
            identifier_external_id = dt['External ID'].split('.',1)[1]
            module_internal_category = dt['Internal Category'].split('.',1)[0]
            identifier_internal_category = dt['Internal Category'].split('.',1)[1]
            module_uom = dt['Unit of Measure'].split('.',1)[0]
            identifier_uom = dt['Unit of Measure'].split('.',1)[1]

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_internal_category, identifier_internal_category))
            category_id = int(cr.fetchone()[0])

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_uom, identifier_uom))
            uom_id = int(cr.fetchone()[0])

            data_structure_template = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                True,
                True,
                category_id,
                dt['Internal Reference'],
                dt['Name'],
                uom_id,
                uom_id,
                0.0,
                'fixed',
                1.0,
                True,
                'product'
                )
            product_template+=[data_structure_template]

            

        # SELECT CURRENT LAST ID IN PRODUCT TEMPLATE
        #cr.execute("""SELECT id from product_template ORDER BY id DESC LIMIT 1 """)
        #last_id = cr.fetchone()[0]
        template_id = 106503

        # INSERT PRODUCT TEMPLATE TO TABLE
        cr.executemany("""INSERT INTO product_template 
            (create_uid,create_date,write_date,write_uid,sale_ok,purchase_ok,categ_id,description,name,uom_id,uom_po_id,list_price,mes_type,uos_coeff,active,type)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure_template))])+""")""",product_template)

        finish_time = datetime.now()
        msg = 'Duration to insert %s of product template = %s' % ('1', format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT PRODUCT TEMPLATE AND PRODUCT TEMPLATE EXTERNAL ID
        start_time = datetime.now()
        for dt in data:
            module_external_id = dt['External ID'].split('.',1)[0]
            identifier_external_id = dt['External ID'].split('.',1)[1]

            data_structure_product = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                dt['Internal Reference'],
                dt['Name'],
                template_id,
                True
                )
            product_product+=[data_structure_product]

            data_structure_modeldata = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                True,
                identifier_external_id,
                module_external_id,
                'product.template',
                template_id
                )
            ir_model_data+=[data_structure_modeldata]
            template_id +=1

        cr.executemany("""INSERT INTO ir_model_data 
            (create_uid, create_date, write_date, write_uid, noupdate, name, module, model, res_id)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure_modeldata))])+""")""",ir_model_data)

        cr.executemany("""INSERT INTO product_product 
            (create_uid, create_date, write_date, write_uid, default_code, name_template, product_tmpl_id, active)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure_product))])+""")""",product_product)
        finish_time = datetime.now()
        msg = 'Duration to insert %s of product template = %s' % ('1', format(finish_time - start_time))
        _logger.warning(msg)
        

        end_time = datetime.now()
        msg = 'Duration to upload all datas = %s' % (format(end_time - begin_time))
        _logger.warning(msg)
#        return json.dumps({'status':'OK','message':result})
	return True
