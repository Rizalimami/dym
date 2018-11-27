from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import fields, osv, orm

class dym_report_pembelian_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_pembelian_print, self).__init__(cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({'formatLang_zero2blank': self.formatLang_zero2blank})

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        division = data['division']
        state = data['state']
        branch_ids = data['branch_ids']
        start_date = data['start_date']
        end_date = data['end_date']
        product_ids = data['product_ids']
        partner_ids = data['partner_ids']
        segmen = data['segmen']
        branch_status = data['branch_status']
        
        where_division = " 1=1 "
        if division :
            where_division = " ai.division = '%s'" % str(division)
	    where_sp_division = " AND sp.division = '%s'" % str(division)
        where_start_date = " 1=1 "
        if start_date :
            where_start_date = " ai.date_invoice >= '%s'" % str(start_date)
        where_end_date = " 1=1 "
        if end_date :
            where_end_date = " ai.date_invoice <= '%s'" % str(end_date)
        where_state = " 1=1 "
        if state in ['open','paid'] :
            where_state = " ai.state = '%s'" % str(state)
        else :
            where_state = " ai.state in ('open','paid')"
        where_branch_ids = " 1=1 "
        if branch_ids :
            where_branch_ids = " ai.branch_id in %s" % str(
                tuple(branch_ids)).replace(',)', ')')
        where_product_ids = " 1=1 "
        if product_ids :
            where_product_ids = " ail.product_id in %s" % str(
                tuple(product_ids)).replace(',)', ')')
        where_partner_ids = " 1=1 "
        if partner_ids :
            where_partner_ids = " ai.partner_id in %s" % str(
                tuple(partner_ids)).replace(',)', ')')
        
        query_pembelian = """
            select ail.id as ail_id, b.branch_status as branch_status, b.code as branch_code, b.name as branch_name, ai.division as division, ai.number as inv_number, to_char(ai.date_invoice,'DD-MM-YYYY') as date_invoice, ai.origin as origin, 
            CASE 
                WHEN ai.state = 'open' THEN 'Open' 
                WHEN ai.state = 'done' THEN 'Done' 
                WHEN ai.state IS NULL THEN '' 
                ELSE ai.state 
            END as state, 
            product.name_template as type, COALESCE(pav.code,'') as warna, prod_cat.name as prod_categ_name, 
            ail.quantity as qty, 
            --case when ci.date is null then 0 when ci.date <= '"""+ str(end_date) + """'then   ail.consolidated_qty else 0 end as consolidated_qty, 
	        --case when  ci.date is null then  ail.consolidated_qty  when ci.date <= '"""+ str(end_date) + """' then 0 else   ail.consolidated_qty end   as unconsolidated_qty,
            --ail.consolidated_qty as consolidated_qty, 
            --ail.quantity - ail.consolidated_qty as unconsolidated_qty,
            ail.consolidated_qty as consolidated_qty, 
            0 as unconsolidated_qty,
            prod.default_code as prod_desc,
            ail.price_unit as price_unit, ail.discount as discount, ail.discount_amount as disc_amount,
            CASE 
                WHEN ail.quantity = 0 THEN 0 
                ELSE ail.price_subtotal / ail.quantity
            END as sales_per_unit,  
            ail.quantity*ail.price_unit as total_sales,
            ail.discount_cash as discount_cash_avg,
            ail.discount_program as discount_program_avg,
            ail.id as id_ail,
            p.name as purchase_name,
            to_char(p.date_order,'DD-MM-YYYY') as purchase_date,
            ail.discount_lain as discount_lain_avg,
            ail.price_subtotal as total_dpp,
            ail.price_subtotal * 0.1 as total_ppn,
            ail.price_subtotal as total_hutang,
            ai.supplier_invoice_number as supplier_invoice_number,
            substring(pr.display_name,2,15) as supplier_code, 
            pr.name as supplier_name,
            acc.code as account_code,
            to_char(ai.document_date,'DD-MM-YYYY') as document_date,
            ai.analytic_4 as account_analytic_id,
            retur.tgl_retur as tgl_retur,
            retur.no_retur as no_retur,
            retur.qty_retur as qty_retur,
            retur.retur_total as retur_total,
            dp.date as tgl_grn,
            dp.name as no_grn,
            prod.id as product_id,
            ail.template_id
            from account_invoice ai inner join account_invoice_line ail on ai.id = ail.invoice_id
            inner join (select tent_ai.id, COALESCE(sum(tent_ail.quantity),0) as total_qty from account_invoice tent_ai inner join account_invoice_line tent_ail on tent_ai.id = tent_ail.invoice_id group by tent_ai.id) tent on ai.id = tent.id
            left join account_account acc on ai.account_id = acc.id
            left join dym_branch b on ai.branch_id = b.id
            left join purchase_order_line pl on ail.purchase_line_id = pl.id
            left join purchase_order p on pl.order_id = p.id
            left join res_partner pr on ai.partner_id = pr.id
            left join product_product product on product.id = ail.product_id
            left join product_product prod on product.name_template = prod.name_template and prod.default_code is not null
            left join product_attribute_value_product_product_rel pavpp on pavpp.prod_id = product.id
            left join product_attribute_value pav on pav.id = pavpp.att_id
            left join product_template prod_template on product.product_tmpl_id = prod_template.id
            left join product_category prod_cat_last on prod_template.categ_id = prod_cat_last.id
            left join product_category prod_cat on prod_cat_last.parent_id = prod_cat.id
            left join (
                select r.date as tgl_retur,r.name as no_retur, sum(rl.product_qty) as qty_retur ,rl.invoice_line_id, sum((rl.price_unit*rl.product_qty)-rl.discount_amount) as retur_total
                from dym_retur_beli_line rl left join dym_retur_beli r on r.id = rl.retur_id
                where r.state in ('approved','except_picking','except_invoice','done')
                group by rl.invoice_line_id,r.date ,r.name 
            ) retur ON retur.invoice_line_id = ail.id
            left join stock_picking sp on ai.origin = sp.origin """ + where_sp_division + """
            left join dym_stock_packing dp on sp.id=dp.picking_id

        """
        where = "WHERE  (ail.purchase_line_id is not null OR ai.tipe = 'purchase') AND ai.type = 'in_invoice' AND " + where_division + " AND " + where_state + " AND " + where_branch_ids + " AND " + where_start_date + " AND " + where_end_date + " AND " + where_product_ids + " AND " + where_partner_ids
        order = "order by b.code, ai.date_invoice, ai.number"
        #print query_pembelian + where + order
        self.cr.execute(query_pembelian + where + order)
        all_lines = self.cr.dictfetchall()
        #print all_lines
        move_lines = []
        if all_lines :
            datas = map(lambda x : {
                'ail_id': x['ail_id'],
                'no': 0,
                'prod_desc': str(x['prod_desc'].encode('ascii','ignore').decode('ascii')) if x['prod_desc'] != None else '',
                'account_code': str(x['account_code'].encode('ascii','ignore').decode('ascii')) if x['account_code'] != None else '',
                'branch_status': str(x['branch_status'].encode('ascii','ignore').decode('ascii')) if x['branch_status'] != None else '',
                'branch_code': str(x['branch_code'].encode('ascii','ignore').decode('ascii')) if x['branch_code'] != None else '',
                'branch_name': str(x['branch_name'].encode('ascii','ignore').decode('ascii')) if x['branch_name'] != None else '',
                'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                'inv_number': str(x['inv_number'].encode('ascii','ignore').decode('ascii')) if x['inv_number'] != None else '',
                #'inv_number': x['inv_number'],
                'date_invoice':  x['date_invoice'],
                'origin': str(x['purchase_name'].encode('ascii','ignore').decode('ascii')) if x['purchase_name'] != None else str(x['origin'].encode('ascii','ignore').decode('ascii')) if x['origin'] != None else '',
                'purchase_name': str(x['purchase_name'].encode('ascii','ignore').decode('ascii')) if x['purchase_name'] != None else '',
                'purchase_date': str(x['purchase_date'].encode('ascii','ignore').decode('ascii')) if x['purchase_date'] != None else '',
                'state': str(x['state'].encode('ascii','ignore').decode('ascii')) if x['state'] != None else '',
                'type': str(x['type'].encode('ascii','ignore').decode('ascii')) if x['type'] != None else '',
                'warna': str(x['warna'].encode('ascii','ignore').decode('ascii')) if x['warna'] != None else '',
                'prod_categ_name': str(x['prod_categ_name'].encode('ascii','ignore').decode('ascii')) if x['prod_categ_name'] != None else '',
                #'tgl_consol':  x['tgl_consol'],
                'qty': x['qty'],
                #'consolidated_qty': x['consolidated_qty'],
                #'unconsolidated_qty': float(x['qty'] or 0) - float(x['consolidated_qty'] or 0),
                'consolidated_qty':  x['qty'],
                'unconsolidated_qty':0,
                'price_unit': x['price_unit'],
                'discount': x['discount'],
                'disc_amount': x['disc_amount'],
                'sales_per_unit': x['sales_per_unit'],
                'total_sales': x['total_sales'],
                'discount_cash_avg': x['discount_cash_avg'],
                'discount_program_avg': x['discount_program_avg'],
                'discount_lain_avg': x['discount_lain_avg'],
                'total_dpp': x['total_dpp'],
                'total_ppn': 0,
                'total_hutang': x['total_dpp'] + 0,
                'no_retur': str(x['no_retur'].encode('ascii','ignore').decode('ascii')) if x['no_retur'] != None else '',
                'tgl_retur': x['tgl_retur'],
                'qty_retur': x['qty_retur'],
                'retur_total': x['retur_total'],
                'consolidate_status' : 'Intransit' if float(x['qty'] or 0) - float(x['consolidated_qty'] or 0) > float(0) else '',
                'supplier_invoice_number': x['supplier_invoice_number'],
                'supplier_name': x['supplier_name'],
                'supplier_code': x['supplier_code'],
                'document_date': x['document_date'],
                'analytic_4': x['account_analytic_id'] if x['account_analytic_id'] != None else '',
                'id_ail': x['id_ail'] if x['id_ail'] != None else '',
                'tgl_grn': x['tgl_grn'],
                'no_grn': x['no_grn'],
                'product_id': x['product_id'],
                'template_id': x['template_id'],
                'tgl_cin': '',
                'no_cin': '',
                }, all_lines)

            total_ppn_per_inv = 0
            amount_tax = 0
            invoice_id = False
            for p in datas:
                if p['id_ail'] not in map(
                        lambda x: x.get('id_ail', None), move_lines):

                    account_invoice_line = filter(
                        lambda x: x['id_ail'] == p['id_ail'], all_lines)
                    analytic_1 = ''
                    analytic_2 = ''
                    analytic_3 = ''
                    analytic_4 = ''
                    analytic_1_name = ''
                    analytic_2_name = ''
                    analytic_3_name = ''
                    analytic_4_name = ''
                    analytic = self.pool.get('account.analytic.account').browse(cr, uid, account_invoice_line[0]['account_analytic_id']) or ''
                    branch_name = ''
                    branch = False
                    branch_status_1 = ''
                    branch_name = ''
                    branch_id = ''
                    if analytic:
                        if analytic.type == 'normal':
                            if analytic.segmen == 1 and analytic_1 == '':
                                analytic_1_name = analytic.name
                                analytic_1 = analytic.code
                            if analytic.segmen == 2 and analytic_2 == '':
                                analytic_2_name = analytic.name
                                analytic_2 = analytic.code
                            if analytic.segmen == 3 and analytic_3 == '':
                                analytic_3_name = analytic.name
                                analytic_3 = analytic.code
                                branch = analytic.branch_id
                                branch_name = branch.name
                                branch_status_1 = branch.branch_status
                                branch_id = branch.id
                            if analytic.segmen == 4 and analytic_4 == '':
                                analytic_4_name = analytic.name
                                analytic_4 = analytic.code
                                analytic_id = analytic
                        while (analytic.parent_id):
                            analytic = analytic.parent_id
                            if analytic.type == 'normal':
                                if analytic.segmen == 1 and analytic_1 == '':
                                    analytic_1_name = analytic.name
                                    analytic_1 = analytic.code
                                if analytic.segmen == 2 and analytic_2 == '':
                                    analytic_2_name = analytic.name
                                    analytic_2 = analytic.code
                                if analytic.segmen == 3 and analytic_3 == '':
                                    analytic_3_name = analytic.name
                                    analytic_3 = analytic.code
                                    branch = analytic.branch_id
                                    branch_name = branch.name
                                    branch_status_1 = branch.branch_status
                                    branch_id = branch.id
                                if analytic.segmen == 4 and analytic_4 == '':
                                    analytic_4_name = analytic.name
                                    analytic_4 = analytic.code
                                    analytic_id == analytic


                        if (branch and branch_ids and branch.id not in branch_ids) or (branch and branch_status and branch_status != branch.branch_status):
                            continue

                        ail = self.pool.get('account.invoice.line').browse(cr, uid, account_invoice_line[0]['ail_id'])
                        if invoice_id != ail.invoice_id.id:
                            '''
                            if round(amount_tax - total_ppn_per_inv,2) != 0 and invoice_id != False:
                                move_lines.append({
                                    'no': '',
                                    'branch_status': '',
                                    'branch_code': '',
                                    'branch_name': '',
                                    'division': '',
                                    'inv_number': '',
                                    'date_invoice': '',
                                    'origin': '',
                                    'purchase_date': '',
                                    'purchase_name': '',
                                    'account_code': '',
                                    'state': '',
                                    'type': '',
                                    'warna': '',
                                    'prod_categ_name': '',
                                    'prod_desc': 'Selisih Pembulatan',
                                    'loan_name': '',
                                    'loan_date': '',
                                    'qty': 0,
                                    'tgl_retur': '',
                                    'no_retur': '',
                                    'qty_retur': 0,
                                    'retur_total': 0,
                                    'consolidated_qty': 0,
                                    'unconsolidated_qty': 0,
                                    'price_unit': 0,
                                    'discount': 0,
                                    'disc_amount': 0,
                                    'sales_per_unit': 0,
                                    'total_sales': 0,
                                    'discount_cash_avg': 0,
                                    'discount_program_avg': 0,
                                    'discount_lain_avg': 0,
                                    'total_dpp': 0,
                                    'total_ppn': 0,
                                    'total_hutang': round(amount_tax - total_ppn_per_inv,2),
                                    'consolidate_status' : '',
                                    'supplier_invoice_number' : '',
                                    'supplier_name' : '',
                                    'supplier_code' : '',
                                    'analytic_1': '',
                                    'analytic_2': '',
                                    'analytic_3': '',
                                    'analytic_4': '',
                                    'analytic_combination': '',
                                    'document_date' : '',
                                    'taxes' : '',
                                    'tgl_grn' : '',
                                    'no_grn' : '',
                                    })
                            invoice_id = ail.invoice_id.id
                            amount_tax = ail.invoice_id.amount_tax
                            total_ppn_per_inv = 0
                            '''
                        analytic_2_branch = analytic_2
                        if analytic_2 in ['210','220','230']:
                            if branch_status_1 == 'H123':
                                analytic_2_branch = analytic_2[:2] + '1'
                            elif branch_status_1 == 'H23':
                                analytic_2_branch = analytic_2[:2] + '2'
                            else:
                                analytic_2_branch = analytic_2
                        analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4
                        p.update({'lines': account_invoice_line})
                        p.update({'analytic_1': analytic_1_name})
                        p.update({'analytic_2': analytic_2_name})
                        p.update({'analytic_3': analytic_3_name})
                        p.update({'analytic_4': analytic_4_name})
                        p.update({'branch_id': branch_id})
                        p.update({'branch_status': branch_status_1})
                        p.update({'branch_name': branch_name})
                        p.update({'analytic_combination': analytic_combination})


                        con_invoice = self.pool.get('consolidate.invoice').search(cr, uid, [('invoice_id', '=', ail.invoice_id.id)])
                        if con_invoice:
                            con_inv = self.pool.get('consolidate.invoice').browse(cr, uid,con_invoice)
                            for con in con_inv:
                                p.update({'tgl_cin': con.date})
                                p.update({'no_cin': con.name})
                                con_invoice_line = self.pool.get('consolidate.invoice.line').search(cr, uid, [('consolidate_id', '=', con.id)])
                                if con_invoice_line:
                                    for con_line in con_invoice_line:
                                        con_inv_line = self.pool.get('consolidate.invoice.line').browse(cr, uid, con_invoice_line)
                                        for con_line_id in con_inv_line:
                                            #print 'zzzzzz', p['product_id'] ,'zzzzzzzzzzzzzzz',con_line_id.product_id.id
                                            #print 'ttttttt', con_line_id.create_date
                                            #if  con_line_id.create_date[:10] > str(end_date) and  p['product_id'] == con_line_id.product_id.id and  p['template_id'] == con_line_id.template_id.id:
                                            if con.date[:10] > str(end_date) and p['product_id'] == con_line_id.product_id.id and p['template_id'] == con_line_id.template_id.id:
                                                p.update({'unconsolidated_qty': p['unconsolidated_qty']+1})
                                                p.update({'consolidated_qty': p['consolidated_qty']-1})


                                                p.update({'unconsolidated_qty': p['unconsolidated_qty'] + p['consolidated_qty']})
                                                p.update({'consolidated_qty': p['qty'] - p['unconsolidated_qty']})
                                                #print 'xxxx',p['unconsolidated_qty']+1
                                                #print 'yyyy', p['consolidated_qty']-1

                        else:
                            p.update({'unconsolidated_qty': p['unconsolidated_qty'] + 1})
                            p.update({'consolidated_qty': p['consolidated_qty'] - 1})

                        if ail and ail.product_id.categ_id:
                            category = ail.product_id.categ_id
                            while (category.parent_id and category.parent_id.bisnis_unit == False):
                                category = category.parent_id
                            p.update({'prod_categ_name': category.name})
                        taxes_name = ''
                        if ail:
                            total_dpp = account_invoice_line[0]['total_dpp']
                            price = (ail.price_unit * ail.quantity) - ail.discount_amount - ail.discount_cash - ail.discount_lain - ail.discount_program
                            taxes = ail.invoice_line_tax_id.compute_all(price, 1, product=ail.product_id, partner=ail.invoice_id.partner_id)
                            total_ppn = 0
                            for tax in taxes['taxes']:
                                total_ppn += tax['amount']
                                taxes_name += tax['name']
                            p.update({'total_ppn': total_ppn})
                            p.update({'total_hutang': total_dpp+total_ppn})
                        p.update({'taxes': taxes_name})
                        loan_ids = self.pool.get('dym.loan').search(cr, uid, [('invoice_ids','=',ail.invoice_id.id),('state','in',['approved','done']),('loan_type','=','Reklasifikasi')]) or False
                        loan_name = ''
                        loan_date = ''
                        if loan_ids:
                            loan = self.pool.get('dym.loan').browse(cr, uid, loan_ids)
                            loan_name = ', '.join(loan.mapped('name'))
                            loan_date = ', '.join(loan.mapped('date'))
                        p.update({'loan_name': loan_name})
                        p.update({'loan_date': loan_date})
                        move_lines.append(p)
                        total_ppn_per_inv += total_ppn
                    # else:
                    #     analytic_4 = ''
                    #     p.update({'lines': account_move_lines})
                    #     p.update({'analytic_1': analytic_1})
                    #     p.update({'analytic_2': analytic_2})
                    #     p.update({'analytic_3': analytic_3})
                    #     p.update({'analytic_4': analytic_4})
                    #     move_lines.append(p)
            reports = filter(lambda x: datas, [{'datas': move_lines}])
        else :
            reports = [{'datas': [{
                'no': 0,
                'branch_status': 'NO DATA FOUND',
                'branch_code': 'NO DATA FOUND',
                'branch_name': 'NO DATA FOUND',
                'division': 'NO DATA FOUND',
                'inv_number': 'NO DATA FOUND',
                'date_invoice': 'NO DATA FOUND',
                'origin': 'NO DATA FOUND',
                'purchase_date': 'NO DATA FOUND',
                'purchase_name': 'NO DATA FOUND',
                'account_code': 'NO DATA FOUND',
                'state': 'NO DATA FOUND',
                'type': 'NO DATA FOUND',
                'warna': 'NO DATA FOUND',
                'prod_categ_name': 'NO DATA FOUND',
                'prod_desc': 'NO DATA FOUND',
                'loan_name': 'NO DATA FOUND',
                'loan_date': 'NO DATA FOUND',
                'qty': 0,
                'consolidated_qty': 0,
                'unconsolidated_qty': 0,
                'price_unit': 0,
                'discount': 0,
                'disc_amount': 0,
                'sales_per_unit': 0,
                'total_sales': 0,
                'discount_cash_avg': 0,
                'discount_program_avg': 0,
                'discount_lain_avg': 0,
                'total_dpp': 0,
                'total_ppn': 0,
                'total_hutang': 0,
                'qty_retur': 0,
                'tgl_retur': 'NO DATA FOUND',
                'no_retur': 'NO DATA FOUND',
                'retur_total' : 0,
                'consolidate_status' : 'NO DATA FOUND',
                'supplier_invoice_number' : 'NO DATA FOUND',
                'supplier_name' : 'NO DATA FOUND',
                'supplier_code' : 'NO DATA FOUND',
                'analytic_1': 'NO DATA FOUND',
                'analytic_2': 'NO DATA FOUND',
                'analytic_3': 'NO DATA FOUND',
                'analytic_4': 'NO DATA FOUND',
                'analytic_combination': 'NO DATA FOUND',
                'document_date' : 'NO DATA FOUND',
                'taxes' : 0,
                'tgl_grn' : 'NO DATA FOUND',
                'no_grn' : 'NO DATA FOUND',
                'tgl_cin': 'NO DATA FOUND',
                'no_cin': 'NO DATA FOUND',
                }]}]
        
        self.localcontext.update({'reports': reports})
        objects=False
        super(dym_report_pembelian_print, self).set_context(objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else :
            return super(dym_report_pembelian_print, self).formatLang(value, digits, date, date_time, grouping, monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_report_pembelian.report_pembelian'
    _inherit = 'report.abstract_report'
    _template = 'dym_report_pembelian.report_pembelian'
    _wrapped_report_class = dym_report_pembelian_print
    