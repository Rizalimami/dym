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

class dym_kelurahan(osv.osv):
    _inherit = "wtc.kelurahan"

    def bulk_kelurahan(self, cr, uid, data, context=None):
	result = []
        dym_kelurahan = []
        ir_model_data = []
        
        # INSERT STOCK LOCATION
        start_time = datetime.now()
        begin_time = start_time

        cr.execute("""SELECT last_value from stock_location_id_seq """)
        res_id = cr.fetchone()[0]

        for dt in data:
            module_external_id = dt['External ID'].split('.',1)[0]
            identifier_external_id = dt['External ID'].split('.',1)[1]
            module_kecamatan = dt['kecamatan_id/id'].split('.',1)[0]
            identifier_kecamatan = dt['kecamatan_id/id'].split('.',1)[1]

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_kecamatan, identifier_kecamatan))
            kecamatan_id = int(cr.fetchone()[0])

            data_structure_kelurahan = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                kecamatan_id,
                dt['code'],
                dt['name']
                )
            dym_kelurahan+=[data_structure_kelurahan]

            data_structure_modeldata = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                True,
                identifier_external_id,
                module_external_id,
                'stock.location',
                res_id
                )
            ir_model_data+=[data_structure_modeldata]
            res_id +=1

            

        # INSERT PRODUCT TEMPLATE TO TABLE
        cr.executemany("""INSERT INTO dym_kelurahan 
            (create_uid,create_date,write_date,write_uid,kecamatan_id,code,name)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure_kelurahan))])+""")""",dym_kelurahan)

        cr.executemany("""INSERT INTO ir_model_data 
            (create_uid, create_date, write_date, write_uid, noupdate, name, module, model, res_id)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure_modeldata))])+""")""",ir_model_data)

        finish_time = datetime.now()
        msg = 'Duration to insert %s of stock location bro = %s' % ('1', format(finish_time - start_time))
        _logger.warning(msg)

       

        end_time = datetime.now()
        msg = 'Duration to upload all datas = %s' % (format(end_time - begin_time))
        _logger.warning(msg)
#        return json.dumps({'status':'OK','message':result})
	return True
