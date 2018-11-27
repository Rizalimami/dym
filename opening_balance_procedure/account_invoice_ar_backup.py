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

class account_invoice(osv.osv):
    _inherit = "account.invoice"

    def _get_analytic_2(self, cr, uid, ids, context=None):
        for x in ids.parent_id:
            if x.segmen == 2 :
                return [x.id]
            else:
                return self._get_analytic_2(cr, uid, x, context=None)
    def bulk_invoice_ar(self, cr, uid, data, context=None):
        result = []
        invoices = []
        invoice_lines = []
        moves = []
        move_lines = []
        # wkf_instances = []
        # wf_service = netsvc.LocalService("workflow")

        # INSERT HEADER INVOICE
        start_time = datetime.now()
        begin_time = start_time
        for dt in data:
            module_analytic = dt['Analytic Account'].split('.',1)[0]
            identifier_analytic = dt['Analytic Account'].split('.',1)[1]
            module_account = dt['Header Account'].split('.',1)[0]
            identifier_account = dt['Header Account'].split('.',1)[1]
            module_branch = dt['Branch'].split('.',1)[0]
            identifier_branch = dt['Branch'].split('.',1)[1]
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]
            
            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
            company_id = int(cr.fetchone()[0])

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
            analytic_4 = cr.fetchone()

            cr.execute("""SELECT parent_id FROM account_analytic_account WHERE   id = %s """, (analytic_4))
            analytic_3 = cr.fetchone()

            analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, [analytic_3[0]], context=None)
            analytic_2 = self._get_analytic_2(cr, uid, analytic_3, context=None)

            cr.execute("""SELECT id FROM account_analytic_account WHERE   segmen = 1 AND company_id = %s """, ((company_id,)))
            analytic_1 = cr.fetchone()

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_account, identifier_account))
            account_id = int(cr.fetchone()[0])

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_branch, identifier_branch))
            branch_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
            period_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_journal WHERE name = %s AND  company_id = %s """, (dt['Journal'], company_id))
            journal_id = int(cr.fetchone()[0])
            

            data_structure = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                dt['Division'],
                dt['Partner'],
                dt['Source Document'],
                dt['Supplier Invoice Number'],
                dt['Due Date'],
                branch_id,
                journal_id,
                period_id,
                analytic_1[0],
                analytic_2[0],
                analytic_3.id,
                analytic_4[0],
                dt['Date'],
                company_id,
                'open',
                13,
                'none',
                dt['Invoice Type'],
                account_id,
                dt['Line / Price Unit'],
                dt['Line / Price Unit'],
                )
            invoices+=[data_structure]
        cr.executemany("""INSERT INTO account_invoice 
            (create_uid,create_date,write_date,write_uid,division,partner_id,origin,supplier_invoice_number,date_due,branch_id,journal_id,period_id,analytic_1,analytic_2,analytic_3,analytic_4,date_invoice,company_id,state,currency_id,reference_type,type,account_id,amount_total,residual)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure))])+""")""",invoices)
        
        finish_time = datetime.now()
        msg = 'Duration to insert %s of account invoice = %s' % (len(data), format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT DETAIL INVOICE
        start_time = datetime.now()
        for dt in data:
            module_analytic = dt['Analytic Account'].split('.',1)[0]
            identifier_analytic = dt['Analytic Account'].split('.',1)[1]
            module_account = dt['Line / Account'].split('.',1)[0]
            identifier_account = dt['Line / Account'].split('.',1)[1]
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]
            
            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
            company_id = int(cr.fetchone()[0])

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
            account_analytic_id = cr.fetchone()

            cr.execute("""SELECT parent_id FROM account_analytic_account WHERE   id = %s """, (account_analytic_id))
            analytic_3 = cr.fetchone()

            analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, [analytic_3[0]], context=None)
            analytic_2 = self._get_analytic_2(cr, uid, analytic_3)

            cr.execute("""SELECT id FROM account_analytic_account WHERE   segmen = 1 AND company_id = %s """, ((company_id,)))
            analytic_1 = cr.fetchone()

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_account, identifier_account))
            account_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_invoice WHERE origin = %s LIMIT 1""", (dt['Source Document'],))
            invoice_id = cr.fetchone()

            data_structure = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                dt['Source Document'],
                account_id,
		        invoice_id[0],
                #analytic_1[0],
                #analytic_2[0],
                #analytic_3.id,
                account_analytic_id[0],
                company_id,
                dt['Line / Price Unit'],
                1,
                dt['Line / Price Unit'],
                )
            invoice_lines.append(data_structure)
            

        cr.executemany("""INSERT INTO account_invoice_line 
            (create_uid,create_date,write_date,write_uid,name,account_id,invoice_id,account_analytic_id,company_id,price_unit,quantity,price_subtotal)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure))])+""")""",invoice_lines)
         
        finish_time = datetime.now()
        msg = 'Duration to insert %s of account invoice line = %s' % (len(data), format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT ACCOUNT MOVE BASED ON INVOICE ABOVE
        start_time = datetime.now()
        for m in data:
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
            company_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_invoice WHERE origin = %s LIMIT 1 """, (m['Source Document'],))
            invoice_id = cr.fetchone()

            cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
            period_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_journal WHERE name = %s AND  company_id = %s """, (dt['Journal'], company_id))
            journal_id = int(cr.fetchone()[0])
	
            data_structure = (
                1,
                datetime.now(),
                datetime.now(),
                1,
                m['Source Document'],
                company_id,
                journal_id,
                period_id,
                m['Date'],
                m['Source Document'],
                dt['Partner'],
                'draft',
                invoice_id[0],
                'account.invoice'
                )
            moves += [data_structure]

        cr.executemany("""INSERT INTO account_move 
            (create_uid,create_date,write_date,write_uid,name,company_id,journal_id,period_id,date,ref,partner_id,state, transaction_id,model)
            VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure))])+""")""",moves)
        
        finish_time = datetime.now()
        msg = 'Duration to insert %s of account move = %s' % (len(data), format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT ACCOUNT MOVE LINE BASED ON ACCOUNT MOVE ABOVE
        start_time = datetime.now()
        for m in data:
            module_analytic = m['Analytic Account'].split('.',1)[0]
            identifier_analytic = m['Analytic Account'].split('.',1)[1]
            module_header_account = m['Header Account'].split('.',1)[0]
            identifier_header_account = m['Header Account'].split('.',1)[1]
            module_detail_account = dt['Line / Account'].split('.',1)[0]
            identifier_detail_account = dt['Line / Account'].split('.',1)[1]
            module_branch = dt['Branch'].split('.',1)[0]
            identifier_branch = dt['Branch'].split('.',1)[1]
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
            company_id = int(cr.fetchone()[0])

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_branch, identifier_branch))
            branch_id = int(cr.fetchone()[0])
            
            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
            analytic_4 = cr.fetchone()

            cr.execute("""SELECT parent_id FROM account_analytic_account WHERE   id = %s """, (analytic_4))
            analytic_3 = cr.fetchone()

            analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, [analytic_3[0]], context=None)
            analytic_2 = self._get_analytic_2(cr, uid, analytic_3)

            cr.execute("""SELECT id FROM account_analytic_account WHERE   segmen = 1 AND company_id = %s """, ((company_id,)))
            analytic_1 = cr.fetchone()

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_header_account, identifier_header_account))
            header_account_id = cr.fetchone()

            cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_detail_account, identifier_detail_account))
            detail_account_id = cr.fetchone()

            cr.execute("""SELECT id FROM account_move WHERE name = %s """, (m['Source Document'],))
            move_id = cr.fetchone()

            cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
            period_id = int(cr.fetchone()[0])

            cr.execute("""SELECT id FROM account_journal WHERE name = %s AND  company_id = %s """, (dt['Journal'], company_id))
            journal_id = int(cr.fetchone()[0])


            if m['Invoice Type'] == 'out_invoice':
                data_structure = (
                    1,
                    datetime.now(),
                    datetime.now(),
                    1,
                    move_id[0],
                    m['Source Document'], 
                    m['Source Document'], 
                    13, 
                    0.0, 
                    m['Due Date'], 
                    period_id, 
                    float(m['Line / Price Unit']), 
                    m["Date"], 
                    dt['Partner'] or None, 
                    header_account_id[0] or None,
                    journal_id,
                    'valid',
                    'normal',
                    company_id,
                    branch_id,
                    m['Division'],
                    analytic_4[0],
                    #analytic_3.id,
                    #analytic_2[0],
                    #analytic_1[0]
                    )
                move_lines+=[data_structure,
                    (
                    1,
                    datetime.now(),
                    datetime.now(),
                    1,
                    move_id[0],
                    m['Source Document'], 
                    m['Source Document'],
                    13, 
                    float(m['Line / Price Unit']), 
                    m['Due Date'], 
                    period_id, 
                    0.0, 
                    m["Date"], 
                    dt['Partner'] or None, 
                    detail_account_id[0] or None,
                    journal_id,
                    'valid',
                    'normal',
                    company_id,
                    branch_id,
                    m['Division'],
                    analytic_4[0],
                    #analytic_3.id,
                    #analytic_2[0],
                    #analytic_1[0]
                    )]
            elif m['Invoice Type'] == 'in_invoice':
                data_structure = (
                    1,
                    datetime.now(),
                    datetime.now(),
                    1,
                    move_id[0],
                    m['Source Document'], 
                    m['Source Document'], 
                    13, 
                    float(m['Line / Price Unit']),
                    m['Due Date'], 
                    period_id, 
                    0.0, 
                    m["Date"], 
                    dt['Partner'] or None, 
                    header_account_id[0] or None,
                    journal_id,
                    'valid',
                    'normal',
                    company_id,
                    branch_id,
                    m['Division'],
                    analytic_4[0],
                    #analytic_3.id,
                    #analytic_2[0],
                    #analytic_1[0]
                    )
                move_lines+=[data_structure,
                    (
                    1,
                    datetime.now(),
                    datetime.now(),
                    1,
                    move_id[0],
                    m['Source Document'], 
                    m['Source Document'],
                    13, 
                    0.0, 
                    m['Due Date'], 
                    period_id, 
                    float(m['Line / Price Unit']), 
                    m["Date"], 
                    dt['Partner'] or None, 
                    detail_account_id[0] or None,
                    journal_id,
                    'valid',
                    'normal',
                    company_id,
                    branch_id,
                    m['Division'],
                    analytic_4[0],
                    #analytic_3.id,
                    #analytic_2[0],
                    #analytic_1[0]
                    )]

        cr.executemany("""INSERT INTO account_move_line (
                create_uid,
                create_date,
                write_date,
                write_uid,
                move_id,
                name,
                ref,
                currency_id,
                credit,
                date_maturity,
                period_id,
                debit,
                date,
                partner_id,
                account_id,
                journal_id,
                state,
                centralisation,
                company_id,
                branch_id,
                division,
                analytic_account_id
                ) VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure))])+""")""",move_lines)

        finish_time = datetime.now()
        msg = 'Duration to insert %s of account move lines = %s' % (len(data) * 2, format(finish_time - start_time))
        _logger.warning(msg)

        cr.execute("""UPDATE account_invoice set move_id = (SELECT id FROM account_move am WHERE account_invoice.origin = am.ref LIMIT 1) """)
        end_time = datetime.now()
        msg = 'Duration to upload all datas = %s' % (format(end_time - begin_time))
        _logger.warning(msg)
        return json.dumps({'status':'OK','message':result})
