
import time
from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
from openerp import SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)


class dym_detail_account_journal_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_detail_account_journal_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })
            
    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        branch_ids = data['branch_ids']
        account_ids = data['account_ids']
        journal_ids = data['journal_ids']
        partner_ids = data['partner_ids']
        division = data['division']
        period_id = data['period_id']
        start_date = data['start_date']
        end_date = data['end_date']
        segmen = data['segmen']
        branch_status = data['branch_status']
        
        user_brw = self.pool.get('res.users').browse(cr, uid, uid)
        user_branch_type = user_brw.branch_type

        title_prefix = ''
        title_short_prefix = ''

        report_journal_detail_account = {
            'type': 'Journal_Account_Detail',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN JOURNAL'),
            'start_date': start_date,
            'end_date': end_date          
            }  
        
        where_period = " 1=1 "
        if period_id:
            where_period = " ap.id = %s" % str(period_id[0])
        where_account = " 1=1 "
        if account_ids :
            where_account=" a.id  in %s " % str(
                tuple(account_ids)).replace(',)', ')')  
                            
        where_branch = " 1=1 "
        if branch_ids :
            branch_ids = branch_ids
            #where_branch = " b.id in %s " % str(
            where_branch = " l.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
            where_branch2 = " branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        else :
            area_user = self.pool.get('res.users').browse(cr,uid,uid).branch_ids
            branch_ids_user = [b.id for b in area_user]
            branch_ids = branch_ids_user
            #where_branch = " b.id in %s " % str(
            where_branch = " l.branch_id in %s " % str(
                tuple(branch_ids_user))
            where_branch2 = " branch_id in %s " % str(
                tuple(branch_ids_user))
            
        where_journal = " 1=1 "
        if journal_ids :
            where_journal=" j.id  in %s " % str(
                tuple(journal_ids)).replace(',)', ')')   
        
        where_partner = " 1=1 "
        if partner_ids :
            where_partner=" p.id  in %s " % str(
                tuple(partner_ids)).replace(',)', ')')
                          
        where_division = " 1=1 "
        if division == 'Unit' :
            where_division=" l.division = 'Unit' "
        elif division == 'Sparepart' :
            where_division=" l.division = 'Sparepart' "  
        elif division == 'Umum' :
            where_division=" l.division = 'Umum' "  
                        
        where_start_date = " 1=1 "
        where_end_date = " 1=1 "                               
        if start_date :
            where_start_date = " l.date >= '%s' " % start_date
        if end_date :
            where_end_date = " l.date <= '%s' " % end_date         

        query_journal_account_detail = "SELECT l.id as id, a.code as account_code, a.name as account_name, '' as account_sap, "\
        "l.division as division, "\
        "l.date as tanggal, "\
        "l.analytic_account_id as analytic_account_id, "\
        "m.name as no_sistem, "\
        "l.name as no_bukti, "\
        "case when l.ref like '%/%' "\
            "then l.ref "\
            "else m.name "\
        "end as keterangan, "\
        "l.debit as debit, "\
        "l.credit as credit, "\
        "r.name as reconcile_name, "\
        "j.name as journal_name, "\
        "ap.code as perid_code, "\
        "case when p3.name is not null "\
                "then p3.default_code "\
                "else p.default_code "\
        "end as partner_code, "\
        "aa.id as analytic_konsolidasi, " \
        "case when p3.name is not null " \
                "then p3.name " \
                "else p.name " \
        "end as partner_name, " \
        "p2.name as cust_suppl, " \
        "loa.branch as branch_x " \
        "FROM account_move_line l "\
        "LEFT JOIN account_move m ON m.id = l.move_id "\
        "LEFT JOIN account_period ap ON ap.id = m.period_id "\
        "LEFT JOIN account_account a ON a.id = l.account_id "\
        "LEFT JOIN account_account_partner aap on aap.account_id=a.id and l.branch_id=aap.branch_id "\
        "LEFT JOIN account_journal j ON j.id = l.journal_id "\
        "LEFT JOIN account_move_reconcile r ON r.id = l.reconcile_id or r.id = l.reconcile_partial_id "\
        "LEFT JOIN res_partner p ON p.id = l.partner_id "\
        "LEFT JOIN res_partner p3 on p3.id = aap.partner_id "\
        "LEFT JOIN res_company c ON (c.partner_id = p.id or p.name = c.name) and p.partner_type = 'Konsolidasi' "\
        "LEFT JOIN account_analytic_account aa ON aa.company_id = c.id and aa.parent_id is null "\
        "LEFT JOIN account_invoice ai on ai.number=m.name "\
        "LEFT JOIN account_voucher av on av.number=m.name "\
        "LEFT JOIN res_partner p2 on p2.id=av.partner_id or p2.id=ai.partner_id " \
        "LEFT JOIN(select dl.name, aa.name branch from dym_loan dl left join account_analytic_account aa on aa.id = dl.analytic_3) loa " \
        "on m.name = loa.name " \
        "WHERE a.type != 'view' AND a.type != 'consolidation' AND a.type != 'closed' "\
        "AND "+where_period+" AND "+where_account+" AND "+where_journal+" AND "+where_division+" AND "+where_start_date+" AND "+where_end_date+" AND "+where_partner+" AND ("+where_branch+" or l.analytic_account_id in (select id from account_analytic_account where  "+ where_branch2 +") ) "\
        "ORDER BY a.name, l.date"
        
        move_selection = ""
        report_info = _('')
        move_selection += ""

        #print query_journal_account_detail
        reports = [report_journal_detail_account]
                
        for report in reports:
            cr.execute(query_journal_account_detail)

            all_lines = cr.dictfetchall()
                
            move_lines = []            
            if all_lines:

                p_map = map(
                    lambda x: {       
                        'no':0,        
                        'perid_code' : x['perid_code'].encode('ascii','ignore').decode('ascii') if x['perid_code'] != None else '',                                                      
                        'account_code': x['account_code'].encode('ascii','ignore').decode('ascii') if x['account_code'] != None else '',
                        'account_name': x['account_name'].encode('ascii','ignore').decode('ascii') if x['account_name'] != None else '',
                        'division': x['division'].encode('ascii','ignore').decode('ascii') if x['division'] != None else '',
                        'tanggal': x['tanggal'] if x['tanggal'] != None else '',  
                        'no_sistem': x['no_sistem'].encode('ascii','ignore').decode('ascii') if x['no_sistem'] != None else '',
                        'no_bukti': x['no_bukti'].encode('ascii','ignore').decode('ascii') if x['no_bukti'] != None else '',
                        'keterangan': x['keterangan'].encode('ascii','ignore').decode('ascii') if x['keterangan'] != None else '',
                        'debit': x['debit'],
                        'credit': x['credit'],
                        'reconcile_name': x['reconcile_name'].encode('ascii','ignore').decode('ascii') if x['reconcile_name'] != None else '',
                        'journal_name': x['journal_name'].encode('ascii','ignore').decode('ascii') if x['journal_name'] != None else '',
                        'partner_code': x['partner_code'].encode('ascii','ignore').decode('ascii') if x['partner_code'] != None else '',
                        'partner_name': x['partner_name'].encode('ascii','ignore').decode('ascii') if x['partner_name'] != None else '',
                        'cust_suppl': x['cust_suppl'].encode('ascii','ignore').decode('ascii') if x['cust_suppl'] != None else '',
                        'analytic_4': x['analytic_account_id'] if x['analytic_account_id'] != None else '',
                        'id': x['id'],
                        'analytic_konsolidasi': x['analytic_konsolidasi'] if x['analytic_konsolidasi'] != None else '',
                        'branch_x': x['branch_x'].encode('ascii', 'ignore').decode('ascii') if x['branch_x'] != None else '',
                        },
                    all_lines)

                for p in p_map:
                    if p['id'] not in map(lambda x: x.get('id', None), move_lines):
                        account_move_lines = filter(
                            lambda x: x['id'] == p['id'], all_lines)
                        analytic_1 = ''
                        analytic_2 = ''
                        analytic_3 = ''
                        analytic_4 = ''
                        analytic_1_name = ''
                        analytic_2_name = ''
                        analytic_3_name = ''
                        analytic_4_name = ''
                        if user_branch_type == 'HO':
                            analytic = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, account_move_lines[0]['analytic_account_id']) or ''
                        else:
                            analytic = self.pool.get('account.analytic.account').browse(cr, uid, account_move_lines[0]['analytic_account_id']) or ''

                        if  p['no_sistem'][:3]=="LOA":
                            #print p['no_sistem'] ,'vvvvvvvvvvvvvv',str(tuple(account_ids)).replace(',)', ')')
                            move_a = self.pool.get('account.move.line').search(cr, uid, [('name', '=', p['no_sistem']),('ref', '!=', p['no_sistem']),('debit' ,'>', 0),('account_id','not in', str(tuple(account_ids)).replace(',)', ')')) ])
                            move_x = self.pool.get('account.move.line').browse(cr, uid, move_a)
                            branch_name =''
                            branch_id = ''
                            for moves in move_x:
                                if branch_name:
                                    branch_name =branch_name, moves.branch_id.name
                                    branch_id = branch_id, moves.branch_id.id
                                    #print branch_id,'mmmm', branch_name
                                else:
                                    branch_name = moves.branch_id.name
                                    branch_id =  moves.branch_id.id


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
                            analytic_2_branch = analytic_2
                            if analytic_2 in ['210','220','230']:
                                if branch_status_1 == 'H123':
                                    analytic_2_branch = analytic_2[:2] + '1'
                                elif branch_status_1 == 'H23':
                                    analytic_2_branch = analytic_2[:2] + '2'
                                else:
                                    analytic_2_branch = analytic_2
                            analytic_combination = analytic_1 + '/' + analytic_2_branch + '/' + analytic_3 + '/' + analytic_4
                            p.update({'lines': account_move_lines})
                            p.update({'analytic_1': analytic_1_name})
                            p.update({'analytic_2': analytic_2_name})
                            p.update({'analytic_3': analytic_3_name})
                            p.update({'analytic_4': analytic_4_name})
                            p.update({'branch_id': branch_id})
                            p.update({'branch_status': branch_status_1})
                            p.update({'branch_name': branch_name})
                            p.update({'analytic_combination': analytic_combination})
                            if account_move_lines[0]['analytic_konsolidasi']:
                                if user_branch_type == 'HO':
                                    analytic_konsolidasi = self.pool.get('account.analytic.account').browse(cr, SUPERUSER_ID, account_move_lines[0]['analytic_konsolidasi'])
                                else:
                                    analytic_konsolidasi = self.pool.get('account.analytic.account').browse(cr, uid, account_move_lines[0]['analytic_konsolidasi'])
                                p.update({'analytic_konsolidasi': analytic_konsolidasi.code})
                            move_lines.append(p)
                        # else:
                        #     analytic_4 = ''
                        #     p.update({'lines': account_move_lines})
                        #     p.update({'analytic_1': analytic_1})
                        #     p.update({'analytic_2': analytic_2})
                        #     p.update({'analytic_3': analytic_3})
                        #     p.update({'analytic_4': analytic_4})
                        #     move_lines.append(p)
                report.update({'move_lines': move_lines})

        reports = filter(lambda x: x.get('move_lines'), reports)
        if not reports:
            reports = [{
            'type': 'Journal_Account_Detail',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('LAPORAN JOURNAL'),
            'start_date': start_date,
            'end_date': end_date  ,
                        'move_lines':
                            [{       
                        'no':0,   
                        'perid_code': 'NO DATA FOUND',                                  
                        'account_code': 'NO DATA FOUND',
                        'account_name': 'NO DATA FOUND',
                        'division': 'NO DATA FOUND',
                        'tanggal': 'NO DATA FOUND',  
                        'no_sistem': 'NO DATA FOUND',
                        'no_bukti': 'NO DATA FOUND',
                        'keterangan': 'NO DATA FOUND',
                        'debit': 0.0,
                        'credit': 0.0,
                        'reconcile_name': 'NO DATA FOUND',
                        'journal_name': 'NO DATA FOUND',
                        'partner_code': 'NO DATA FOUND',
                        'partner_name': 'NO DATA FOUND',
                        'cust_suppl': 'NO DATA FOUND',
                        'analytic_1': 'NO DATA FOUND',
                        'analytic_2': 'NO DATA FOUND',
                        'analytic_3': 'NO DATA FOUND',
                        'analytic_4': 'NO DATA FOUND',
                        'analytic_konsolidasi': 'NO DATA FOUND',
                        'analytic_combination': 'NO DATA FOUND',
                        'branch_status': 'NO DATA FOUND',
                        'branch_name': 'NO DATA FOUND',
                        'branch_x': 'NO DATA FOUND',
                        }], 
                        
            }]
        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
            })
        objects=False
        super(dym_detail_account_journal_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_detail_account_journal_report_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_account_move.report_journal_detail_account'
    _inherit = 'report.abstract_report'
    _template = 'dym_account_move.report_journal_detail_account'
    _wrapped_report_class = dym_detail_account_journal_report_print
