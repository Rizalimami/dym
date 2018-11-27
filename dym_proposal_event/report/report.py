from datetime import datetime
from openerp.osv.fields import datetime as datetime_field
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.report import report_sxw
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class dym_report_proposal_event_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_report_proposal_event_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def get_pay_array(self, cr, uid, desc_opex='', bud_opex=0, act_opex=0, type_target='', warna_target='', qty_target=0, act_target=0, tipe_partner='',partner='', amount=0, proposal_event=[]):
        res = {
            'no': '',
            'branch_id': '',
            'division': '',
            'activity': '',
            'address': '',
            'start_date': '',
            'end_date': '',
            'pic': '',
            'desc_opex': desc_opex,
            'bud_opex': bud_opex,
            'act_opex': act_opex,
            'type_target': type_target,
            'warna_target': warna_target,
            'qty_target': qty_target,
            'act_target': act_target,
            'tipe_partner': tipe_partner,
            'partner': partner,
            'amount': amount,
            'lines': proposal_event,
        }
        return res

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context

        start_date = False
        end_date = False
        division = False
        branch_ids = False
        
        if data:
            start_date = data.get('start_date',False)
            end_date = data.get('end_date',False)
            division = data.get('division',False)
            branch_ids = data.get('branch_ids',False)


        title_prefix = ''
        title_short_prefix = ''
        
        report_proposal_event = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Proposal Event')}

        query_start = "SELECT pe.id as id_ai, " \
            "COALESCE(b.name,'') as branch_id, " \
            "COALESCE(pe.division,'') as division, " \
            "COALESCE(pe.name,'') as activity, " \
            "pe.start_date as start_date, " \
            "pe.stop_date as end_date, " \
            "COALESCE(hr.name_related,'') as pic " \
            "FROM " \
            "dym_proposal_event pe " \
            "LEFT JOIN hr_employee hr ON pe.pic = hr.id " \
            "LEFT JOIN dym_branch b ON pe.branch_id = b.id " \
            "where 1=1 AND pe.state in ('approved','done') "
            
        move_selection = ""
        report_info = _('')
        move_selection += ""

        query_end=""
        if start_date:
            query_end +=" AND pe.stop_date >= '%s' " % str(start_date)
        if end_date:
            query_end +=" AND pe.start_date <= '%s' " % str(end_date)
        if division:
            query_end +=" AND pe.division = '%s' " % str(division)
        if branch_ids:
            query_end +=" AND pe.branch_id in %s " % str(
                tuple(branch_ids)).replace(',)', ')')
        reports = [report_proposal_event]
        
        # query_order = "order by cabang"
        query_order = " "
        for report in reports:
            cr.execute(query_start + query_end + query_order)
            all_lines = cr.dictfetchall()
            id_ai = []
            if all_lines:
                p_map = map(
                    lambda x: {
                        'no': '',      
                        'id_ai': x['id_ai'] if x['id_ai'] != None else '',
                        'branch_id': str(x['branch_id'].encode('ascii','ignore').decode('ascii')) if x['branch_id'] != None else '',
                        'division': str(x['division'].encode('ascii','ignore').decode('ascii')) if x['division'] != None else '',
                        'activity': str(x['activity'].encode('ascii','ignore').decode('ascii')) if x['activity'] != None else '',
                        'start_date': str(x['start_date']) if x['start_date'] != None else '',
                        'end_date': str(x['end_date']) if x['end_date'] != None else '',
                        'pic': str(x['pic'].encode('ascii','ignore').decode('ascii')) if x['pic'] != None else '',
                        },
                       
                    all_lines)
                no = 0
                for p in p_map:
                    if p['id_ai'] not in map(
                            lambda x: x.get('id_ai', None), id_ai):
                        proposal_event = filter(
                            lambda x: x['id_ai'] == p['id_ai'], all_lines)
                        proposal = self.pool.get('dym.proposal.event').browse(cr, uid, proposal_event[0]['id_ai'])
                        no += 1
                        address = (proposal.street or '') + (', ' if proposal.street and proposal.street2 else '') + (proposal.street2 or '') + (' RT/RW ' + (proposal.rt or '') + '/' + (proposal.rw or '') if proposal.rt or proposal.rw else '') + ((', Kel. ' + proposal.kelurahan) if proposal.kelurahan else '') + ((', Kec. ' + proposal.kecamatan) if proposal.kecamatan else '') + ((' ' + proposal.city_id.name) if proposal.city_id else '') + ((' ' + proposal.state_id.name) if proposal.state_id else '')
                        p.update({
                            'no': str(no),
                            'address': address,
                            'desc_opex': '',
                            'bud_opex': 0,
                            'act_opex': 0,
                            'type_target': '',
                            'warna_target': '',
                            'qty_target': 0,
                            'act_target': 0,
                            'tipe_partner': '',
                            'partner': '',
                            'amount': 0,
                            'lines': proposal_event,
                        })
                        id_ai.append(p)
                        index = len(id_ai) - 1
                        add_line = []
                        latest_index = index
                        for biaya in proposal.biaya_ids:
                            if id_ai[index]['desc_opex'] == '' and id_ai[index]['bud_opex'] == 0 and id_ai[index]['act_opex'] == 0:
                                id_ai[index]['desc_opex'] = biaya.name
                                id_ai[index]['bud_opex'] = biaya.amount_proposal
                                id_ai[index]['act_opex'] = biaya.amount
                            else:
                                latest_index += 1
                                proposal_res = self.get_pay_array(cr, uid, desc_opex=biaya.name, bud_opex=biaya.amount_proposal, act_opex=biaya.amount, proposal_event=proposal_event)
                                id_ai.append(proposal_res)
                        sub_index = index + 1
                        for target in proposal.target_ids:
                            prod_desc = target.product_id.product_tmpl_id.description or target.product_id.default_code
                            if id_ai[index]['type_target'] == '' and id_ai[index]['warna_target'] == '' and id_ai[index]['qty_target'] == 0 and id_ai[index]['act_target'] == 0:
                                id_ai[index]['type_target'] = prod_desc
                                id_ai[index]['warna_target'] = proposal.branch_id.get_attribute_name(target.product_id)
                                id_ai[index]['qty_target'] = target.qty
                                id_ai[index]['act_target'] = target.qty_sold
                            elif sub_index <= latest_index:
                                id_ai[sub_index]['type_target'] = prod_desc
                                id_ai[sub_index]['warna_target'] = proposal.branch_id.get_attribute_name(target.product_id)
                                id_ai[sub_index]['qty_target'] = target.qty
                                id_ai[sub_index]['act_target'] = target.qty_sold
                                sub_index += 1
                            else:
                                latest_index += 1
                                sub_index += 1
                                proposal_res = self.get_pay_array(cr, uid, type_target=prod_desc, warna_target=proposal.branch_id.get_attribute_name(target.product_id), qty_target=target.qty, act_target=target.qty_sold, proposal_event=proposal_event)
                                id_ai.append(proposal_res)
                        sub_index = index + 1
                        for sharing in proposal.sharing_ids:
                            if id_ai[index]['tipe_partner'] == '' and id_ai[index]['partner'] == '' and id_ai[index]['amount'] == 0:
                                id_ai[index]['tipe_partner'] = sharing.tipe_partner
                                id_ai[index]['partner'] = sharing.sharing_partner.name
                                id_ai[index]['amount'] = sharing.sharing_amount
                            elif sub_index <= latest_index:
                                id_ai[sub_index]['tipe_partner'] = sharing.tipe_partner
                                id_ai[sub_index]['partner'] = sharing.sharing_partner.name
                                id_ai[sub_index]['amount'] = sharing.sharing_amount
                                sub_index += 1
                            else:
                                latest_index += 1
                                sub_index += 1
                                proposal_res = self.get_pay_array(cr, uid, tipe_partner=sharing.tipe_partner, partner=sharing.sharing_partner.name, amount=sharing.sharing_amount, proposal_event=proposal_event)
                                id_ai.append(proposal_res)
                report.update({'id_ai': id_ai})
                # report.update({'id_ai': p_map})

        reports = filter(lambda x: x.get('id_ai'), reports)
        if not reports :
            reports = [{'title_short': 'Laporan Proposal Event', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'id_ai':
                    [{
                        'no': '',
                        'branch_id': 'NO DATA FOUND',
                        'division': 'NO DATA FOUND',
                        'activity': 'NO DATA FOUND',
                        'address': 'NO DATA FOUND',
                        'start_date': 'NO DATA FOUND',
                        'end_date': 'NO DATA FOUND',
                        'pic': 'NO DATA FOUND',
                        'desc_opex': 'NO DATA FOUND',
                        'bud_opex': 0,
                        'act_opex': 0,
                        'type_target': 'NO DATA FOUND',
                        'warna_target': 'NO DATA FOUND',
                        'qty_target': 0,
                        'act_target': 0,
                        'tipe_partner': 'NO DATA FOUND',
                        'partner': 'NO DATA FOUND',
                        'amount': 0,
                    }], 
                    'title': ''
                }]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
        })
        super(dym_report_proposal_event_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_proposal_event_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_proposal_event.report_proposal_event'
    _inherit = 'report.abstract_report'
    _template = 'dym_proposal_event.report_proposal_event'
    _wrapped_report_class = dym_report_proposal_event_print
