# -*- encoding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _
from psycopg2 import IntegrityError, OperationalError, errorcodes
from openerp import netsvc, SUPERUSER_ID
from openerp import workflow
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

        company_cols = {}
        analytic4_cols = {}
        analytic3_cols = {}
        analytic2_cols = {}
        analytic1_cols = {}
        account_cols = {}
        branch_cols = {}
        period_cols = {}
        journal_cols = {}

        invoice_cols = {}
        headeraccount_cols = {}
        detailaccount_cols = {}
        moveid_cols = {}
        company_id_period_cols = {}

        invoice_vals = []

        for n,dt in enumerate(data,start=0):
            module_analytic = dt['Analytic Account'].split('.',1)[0]
            identifier_analytic = dt['Analytic Account'].split('.',1)[1]
            module_account = dt['Header Account'].split('.',1)[0]
            identifier_account = dt['Header Account'].split('.',1)[1]
            module_branch = dt['Branch'].split('.',1)[0]
            identifier_branch = dt['Branch'].split('.',1)[1]
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]
            
            module_company_identifier_company = '%s__%s' % (module_company, identifier_company)
            if not module_company_identifier_company in company_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
                company_id = cr.fetchone()
                company_id = list==type(company_id) and company_id[0] or company_id
                company_cols[module_company_identifier_company]=company_id
            else:
                company_id = company_cols[module_company_identifier_company]

            module_analytic_identifier_analytic = '%s__%s' % (module_analytic, identifier_analytic)
            if not module_analytic_identifier_analytic in analytic4_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
                analytic_4 = cr.fetchone()
                analytic4_cols[module_analytic_identifier_analytic]=analytic_4
            else:
                analytic_4 = analytic4_cols[module_analytic_identifier_analytic]

            if not analytic_4 in analytic3_cols:
                cr.execute("""SELECT parent_id FROM account_analytic_account WHERE   id = %s """, (analytic_4))
                analytic_3 = cr.fetchone()
                analytic_3 = self.pool.get('account.analytic.account').browse(cr, uid, [analytic_3[0]], context=None)
                analytic3_cols[analytic_4]=analytic_3
            else:
                analytic_3 = analytic3_cols[analytic_4]

            if not analytic_3 in analytic2_cols:
                analytic_2 = self._get_analytic_2(cr, uid, analytic_3, context=None)
                analytic2_cols[analytic_3] = analytic_2
            else:
                analytic_2 = analytic2_cols[analytic_3]

            if not company_id in analytic1_cols:
                cr.execute("""SELECT id FROM account_analytic_account WHERE   segmen = 1 AND company_id = %s """, ((company_id,)))
                analytic_1 = cr.fetchone()
                analytic1_cols[company_id] = analytic_1
            else:
                analytic_1 = analytic1_cols[company_id]

            module_account_identifier_account = '%s__%s' % (module_account, identifier_account)
            if not module_account_identifier_account in account_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_account, identifier_account))
                account_id = int(cr.fetchone()[0])
                account_cols[module_account_identifier_account] = account_id
            else:
                account_id = account_cols[module_account_identifier_account]

            module_branch_identifier_branch = '%s__%s' % (module_branch, identifier_branch)
            if not module_branch_identifier_branch in branch_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_branch, identifier_branch))
                branch_id = int(cr.fetchone()[0])
                branch_cols[module_branch_identifier_branch] = branch_id
            else:
                branch_id = branch_cols[module_branch_identifier_branch]

            if not company_id in period_cols:
                cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
                period_id = cr.fetchone()
                period_id = list==type(period_id) and int(period_id[0]) or period_id
                period_cols[company_id] = period_id
            else:
                period_id = period_cols[company_id]

            if not company_id in journal_cols:
                cr.execute("""SELECT id FROM account_journal WHERE name = %s AND  company_id = %s """, (dt['Journal'], company_id))
                journal_id = cr.fetchone()
                journal_id = list==type(journal_id) and int(journal_id[0]) or journal_id 
                journal_cols[company_id] = journal_id
            else:
                journal_id = journal_cols[company_id]

            invoice_vals.append({
                'create_uid' : 1,
                'create_date' : datetime.now(),
                'write_date' : datetime.now(),
                'write_uid' : 1,
                'division' : dt['Division'],
                'partner_id' : dt['Partner'],
                'origin' : dt['Source Document'],
                'supplier_invoice_number' : dt['Supplier Invoice Number'],
                'date_due' : dt['Due Date'],
                'branch_id' : branch_id,
                'journal_id' : journal_id,
                'period_id' : period_id,
                'analytic_1' : list==type(analytic_1) and analytic_1[0] or analytic_1,
                'analytic_2' : list==type(analytic_2) and analytic_2[0] or analytic_2,
                'analytic_3' : analytic_3.id,
                'analytic_4' : list==type(analytic_4) and analytic_4[0] or analytic_4,
                'date_invoice' : dt['Date'],
                'company_id' : company_id,
                'state' : 'open',
                'currency_id' : 13,
                'reference_type' : 'none',
                'type' : dt['Invoice Type'],
                'account_id' : account_id,
                'amount_total' : dt['Line / Price Unit'],
                'residual' : dt['Line / Price Unit'],
                'consolidated': 'Consolidated' in dt and dt['Consolidated'] or True,
            })
    
        invoice_ids = self.insert_many(cr, uid, 'account_invoice', 'origin,id', invoice_vals, context=None)
        inv_ids = [x[1] for x in invoice_ids]
        invoice_ids = dict(invoice_ids)

        #     data_structure = (
        #         1,
        #         datetime.now(),
        #         datetime.now(),
        #         1,
        #         dt['Division'],
        #         dt['Partner'],
        #         dt['Source Document'],
        #         dt['Supplier Invoice Number'],
        #         dt['Due Date'],
        #         branch_id,
        #         journal_id,
        #         period_id,
        #         analytic_1[0],
        #         analytic_2[0],
        #         analytic_3.id,
        #         analytic_4[0],
        #         dt['Date'],
        #         company_id,
        #         'open',
        #         13,
        #         'none',
        #         dt['Invoice Type'],
        #         account_id,
        #         dt['Line / Price Unit'],
        #         dt['Line / Price Unit'],
        #         )
        #     invoices+=[data_structure]
        # cr.executemany("""INSERT INTO account_invoice 
        #     (create_uid,create_date,write_date,write_uid,division,partner_id,origin,supplier_invoice_number,date_due,branch_id,journal_id,period_id,analytic_1,analytic_2,analytic_3,analytic_4,date_invoice,company_id,state,currency_id,reference_type,type,account_id,amount_total,residual)
        #     VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure))])+""")""",invoices)
        
        finish_time = datetime.now()
        msg = 'Duration to insert %s of account invoice = %s' % (len(data), format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT DETAIL INVOICE
        source_document_cols = {}
        start_time = datetime.now()
        for dt in data:
            module_analytic = dt['Analytic Account'].split('.',1)[0]
            identifier_analytic = dt['Analytic Account'].split('.',1)[1]
            module_account = dt['Line / Account'].split('.',1)[0]
            identifier_account = dt['Line / Account'].split('.',1)[1]
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]

            module_company_identifier_company = '%s__%s' % (module_company, identifier_company)
            if not module_company_identifier_company in company_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
                company_id = int(cr.fetchone()[0])
                company_cols[module_company_identifier_company]=company_id
            else:
                company_id = company_cols[module_company_identifier_company]

            module_analytic_identifier_analytic = '%s__%s' % (module_analytic, identifier_analytic)
            if not module_analytic_identifier_analytic in analytic4_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
                analytic_4 = cr.fetchone()
                analytic4_cols[module_analytic_identifier_analytic]=analytic_4
            else:
                analytic_4 = analytic4_cols[module_analytic_identifier_analytic]

            module_account_identifier_account = '%s__%s' % (module_account, identifier_account)
            if not module_account_identifier_account in account_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_account, identifier_account))
                account_id = int(cr.fetchone()[0])
                account_cols[module_account_identifier_account] = account_id
            else:
                account_id = account_cols[module_account_identifier_account]

            #source_document = dt['Source Document']
            #if not source_document in source_document_cols:
            #    cr.execute("""SELECT id FROM account_invoice WHERE origin = %s LIMIT 1""", (dt['Source Document'],))
            #    invoice_id = cr.fetchone()
            #    source_document_cols[source_document] = invoice_id
            #else:
            #    invoice_id = source_document_cols[source_document]
      
            invoice_id = [invoice_ids[dt['Source Document']]]

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
                #account_analytic_id[0],
                analytic_4[0],
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


        for x in inv_ids:
            self.button_compute(cr, uid, [x], context=context)
        for inv_id in inv_ids:
            workflow.trg_create(uid, 'account.invoice', inv_id, cr)
            workflow.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)
        self.action_date_assign(cr, uid, inv_ids)

        # INSERT ACCOUNT MOVE BASED ON INVOICE ABOVE
        company_id_journal_cols = {}
        start_time = datetime.now()
        move_vals = []
        for m in data:
            module_company = dt['Company'].split('.',1)[0]
            identifier_company = dt['Company'].split('.',1)[1]

            module_company_identifier_company = '%s__%s' % (module_company, identifier_company)
            if not module_company_identifier_company in company_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
                company_id = int(cr.fetchone()[0])
                company_cols[module_company_identifier_company]=company_id
            else:
                company_id = company_cols[module_company_identifier_company]

            #module_invoice_identifier_account = '%s' % (dt['Source Document'])
            #if not module_invoice_identifier_account in invoice_cols:
            #    cr.execute("""SELECT id FROM account_invoice WHERE origin = %s LIMIT 1""", (dt['Source Document'],))
            #    invoice_id = cr.fetchone()
            #    invoice_cols[module_invoice_identifier_account] = invoice_id
            #else:
            #    invoice_id = invoice_cols[module_invoice_identifier_account]
            
            invoice_id = [invoice_ids[m['Source Document']]]

            company_id_period = '%s__%s' % (dt['Period'], company_id)
            if not company_id_period in company_id_period_cols:
                cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
                period_id = int(cr.fetchone()[0])
                company_id_period_cols[company_id_period] = period_id
            else:
                period_id = company_id_period_cols[company_id_period]

            company_id_period = '%s__%s' % (dt['Journal'], company_id)
            if not company_id_period in company_id_journal_cols:
                cr.execute("""SELECT id FROM account_journal WHERE name = %s AND  company_id = %s """, (dt['Journal'], company_id))
                journal_id = int(cr.fetchone()[0])
                company_id_journal_cols[company_id_period] = journal_id
            else:
                journal_id = company_id_journal_cols[company_id_period]
    
            # data_structure = (
            #     1,
            #     datetime.now(),
            #     datetime.now(),
            #     1,
            #     m['Source Document'],
            #     company_id,
            #     journal_id,
            #     period_id,
            #     m['Date'],
            #     m['Source Document'],
            #     dt['Partner'],
            #     'draft',
            #     invoice_id[0],
            #     'account.invoice'
            #     )
            # moves += [data_structure]


            move_vals.append({
                'create_uid': 1,
                'create_date': datetime.now(),
                'write_date': datetime.now(),
                'write_uid': 1,
                'name': m['Source Document'],
                'company_id': company_id,
                'journal_id': journal_id,
                'period_id': period_id,
                'date': m['Date'],
                'ref': m['Source Document'],
                'partner_id': m['Partner'],
                'state': 'draft', 
                'transaction_id': invoice_id[0],
                'model': 'account.invoice',
            })

        # cr.executemany("""INSERT INTO account_move 
        #     (create_uid,create_date,write_date,write_uid,name,company_id,journal_id,period_id,date,ref,partner_id,state, transaction_id,model)
        #     VALUES ("""+ ','.join(['%s' for x in range(0, len(data_structure))])+""")""",moves)

        move_ids = self.insert_many(cr, uid, 'account_move', 'id', move_vals, context=None)


        
        finish_time = datetime.now()
        msg = 'Duration to insert %s of account move = %s' % (len(data), format(finish_time - start_time))
        _logger.warning(msg)

        # INSERT ACCOUNT MOVE LINE BASED ON ACCOUNT MOVE ABOVE
        start_time = datetime.now()
        for num,m in enumerate(data,start=0):
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

            module_company_identifier_company = '%s__%s' % (module_company, identifier_company)
            if not module_company_identifier_company in company_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_company, identifier_company))
                company_id = int(cr.fetchone()[0])
                company_cols[module_company_identifier_company]=company_id
            else:
                company_id = company_cols[module_company_identifier_company]

            module_branch_identifier_branch = '%s__%s' % (module_branch, identifier_branch)
            if not module_branch_identifier_branch in branch_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_branch, identifier_branch))
                branch_id = int(cr.fetchone()[0])
                branch_cols[module_branch_identifier_branch] = branch_id
            else:
                branch_id = branch_cols[module_branch_identifier_branch]
            
            module_analytic_identifier_analytic = '%s__%s' % (module_analytic, identifier_analytic)
            if not module_analytic_identifier_analytic in analytic4_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_analytic, identifier_analytic))
                analytic_4 = cr.fetchone()
                analytic4_cols[module_analytic_identifier_analytic]=analytic_4
            else:
                analytic_4 = analytic4_cols[module_analytic_identifier_analytic]

            modul_headeraccount = '%s__%s' % (module_header_account, identifier_header_account)
            if not modul_headeraccount in headeraccount_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_header_account, identifier_header_account))
                header_account_id = cr.fetchone()
                headeraccount_cols[modul_headeraccount] = header_account_id
            else:
                header_account_id = headeraccount_cols[modul_headeraccount]

            module_detailaccount = '%s__%s' % (module_detail_account, identifier_detail_account)
            if not module_detailaccount in detailaccount_cols:
                cr.execute("""SELECT res_id FROM ir_model_data WHERE module = %s AND  name = %s """, (module_detail_account, identifier_detail_account))
                detail_account_id = cr.fetchone()
                detailaccount_cols[module_detailaccount] = detail_account_id
            else:
                detail_account_id = detailaccount_cols[module_detailaccount]

            # module_moveid = '%s' % (m['Source Document'])
            # if not module_moveid in moveid_cols:
            #     cr.execute("""SELECT id FROM account_move WHERE name = %s """, (m['Source Document'],))
            #     move_id = cr.fetchone()
            #     moveid_cols[module_moveid] = move_id
            # else:
            #     move_id = moveid_cols[module_moveid]

            move_id = move_ids[num]

            company_id_period = '%s__%s' % (dt['Period'], company_id)
            if not company_id_period in company_id_period_cols:
                cr.execute("""SELECT id FROM account_period WHERE name = %s AND  company_id = %s """, (dt['Period'], company_id))
                period_id = int(cr.fetchone()[0])
                company_id_period_cols[company_id_period] = period_id
            else:
                period_id = company_id_period_cols[company_id_period]

            company_id_period = '%s__%s' % (dt['Journal'], company_id)
            if not company_id_period in company_id_journal_cols:
                cr.execute("""SELECT id FROM account_journal WHERE name = %s AND  company_id = %s """, (dt['Journal'], company_id))
                journal_id = int(cr.fetchone()[0])
                company_id_journal_cols[company_id_period] = journal_id
            else:
                journal_id = company_id_journal_cols[company_id_period]

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

        # cr.execute("""UPDATE account_invoice set move_id = (SELECT id FROM account_move am WHERE account_invoice.origin = am.ref LIMIT 1) where """)

        invoice_ids = dict(invoice_ids)

        for num,dt in enumerate(data,start=0):
            invoice_id = invoice_ids[dt['Source Document']]
            cr.execute("""UPDATE account_invoice set move_id = %s where id=%s""", (move_ids[num],invoice_id))



        end_time = datetime.now()
        msg = 'Duration to upload all datas = %s' % (format(end_time - begin_time))
        _logger.warning(msg)
        return json.dumps({'status':'OK','message':result})
