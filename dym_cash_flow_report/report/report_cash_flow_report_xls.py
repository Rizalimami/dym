import xlwt
from datetime import datetime, date, timedelta
from openerp import SUPERUSER_ID
from openerp.osv import orm
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import rowcol_to_cell, _render
from .report_cash_flow_report import dym_report_cash_flow_print
from openerp.tools.translate import translate
import logging
_logger = logging.getLogger(__name__)
import string

_ir_translation_name = 'report.cash.flow'

class dym_report_cash_flow_print_xls(dym_report_cash_flow_print):

    def __init__(self, cr, uid, name, context):
        super(dym_report_cash_flow_print_xls, self).__init__(
            cr, uid, name, context=context)
        move_line_obj = self.pool.get('account.move.line')
        self.context = context
        wl_overview = move_line_obj._report_xls_cash_flow_fields(
            cr, uid, [], context)
        tmpl_upd_overview = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        wl_details = move_line_obj._report_xls_arap_details_fields(
            cr, uid, context)
        tmpl_upd_details = move_line_obj._report_xls_arap_overview_template(
            cr, uid, context)
        self.localcontext.update({
            'datetime': datetime,
            'wanted_list_overview': wl_overview,
            'template_update_overview': tmpl_upd_overview,
            'wanted_list_details': wl_details,
            'template_update_details': tmpl_upd_details,
            '_': self._,
        })

    def _(self, src):
        lang = self.context.get('lang', 'en_US')
        return translate(
            self.cr, _ir_translation_name, 'report', lang, src) or src

class report_cash_flow_xls(report_xls):

    def __init__(self, name, table, rml=False,
                 parser=False, header=True, store=False):
        super(report_cash_flow_xls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header

        # Report Column Headers format
        rh_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(
            rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])

        # Partner Column Headers format
        fill_blue = 'pattern: pattern solid, fore_color 27;'
        ph_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.ph_cell_style = xlwt.easyxf(ph_cell_format)
        self.ph_cell_style_decimal = xlwt.easyxf(
            ph_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # Partner Column Data format
        pd_cell_format = _xs['borders_all']
        self.pd_cell_style = xlwt.easyxf(pd_cell_format)
        self.pd_cell_style_center = xlwt.easyxf(
            pd_cell_format + _xs['center'])
        self.pd_cell_style_date = xlwt.easyxf(
            pd_cell_format + _xs['left'],
            num_format_str=report_xls.date_format)
        self.pd_cell_style_decimal = xlwt.easyxf(
            pd_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # totals
        rt_cell_format = _xs['bold'] + _xs['fill'] + _xs['borders_all']
        self.rt_cell_style = xlwt.easyxf(rt_cell_format)
        self.rt_cell_style_right = xlwt.easyxf(rt_cell_format + _xs['right'])
        self.rt_cell_style_decimal = xlwt.easyxf(
            rt_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)

        # XLS Template
        self.col_specs_template_overview = {
            'no': {
                'header': [1, 5, 'text', _render("_('No')")],
                'lines': [1, 0, 'number', _render("p['no']")],
                'totals': [1, 5, 'text', None]},
            'cabang': {
                'header': [1, 23, 'text', _render("_('Cabang')")],
                'lines': [1, 0, 'text', _render("p['cabang']")],
                'totals': [1, 23, 'text', _render("_('Total')")]},
            'division': {
                'header': [1, 23, 'text', _render("_('Divisi')")],
                'lines': [1, 0, 'text', _render("p['division']")],
                'totals': [1, 23, 'text', None]},
            'partner_code': {
                'header': [1, 23, 'text', _render("_('Customer')")],
                'lines': [1, 0, 'text', _render("p['partner_code']")],
                'totals': [1, 23, 'text', None]},
            'partner_name': {
                'header': [1, 23, 'text', _render("_('Nama Customer')")],
                'lines': [1, 0, 'text', _render("p['partner_name']")],
                'totals': [1, 23, 'text', None]},
            'account_type': {
                'header': [1, 23, 'text', _render("_('Tipe Account')")],
                'lines': [1, 0, 'text', _render("p['account_type']")],
                'totals': [1, 23, 'text', None]},
            'account_code': {
                'header': [1, 23, 'text', _render("_('No Rek')")],
                'lines': [1, 0, 'text', _render("p['account_code']")],
                'totals': [1, 23, 'text', None]},
            'account_sap': {
                'header': [1, 23, 'text', _render("_('No SUN')")],
                'lines': [1, 0, 'text', _render("p['account_sap']")],
                'totals': [1, 23, 'text', None]},
            'invoice_name': {
                'header': [1, 23, 'text', _render("_('No Sistem')")],
                'lines': [1, 0, 'text', _render("p['invoice_name']")],
                'totals': [1, 23, 'text', None]},
            'name': {
                'header': [1, 23, 'text', _render("_('Name')")],
                'lines': [1, 0, 'text', _render("p['name']")],
                'totals': [1, 23, 'text', None]},
            'date_aml': {
                'header': [1, 23, 'text', _render("_('Tanggal')")],
                'lines': [1, 0, 'text', _render("p['date_aml']")],
                'totals': [1, 23, 'text', None]},
            'due_date': {
                'header': [1, 23, 'text', _render("_('Tgl Jatuh Tempo')")],
                'lines': [1, 0, 'text', _render("p['due_date']")],
                'totals': [1, 23, 'text', None]},
            'overdue': {
                'header': [1, 23, 'text', _render("_('Overdue')")],
                'lines': [1, 0, 'text', _render("p['overdue']")],
                'totals': [1, 23, 'text', None]},
            'status': {
                'header': [1, 23, 'text', _render("_('Status')")],
                'lines': [1, 0, 'text', _render("p['status']")],
                'totals': [1, 23, 'text', None]},
            'tot_invoice': {
                'header': [1, 23, 'text', _render("_('Total Invoice')")],
                'lines': [1, 0, 'number', _render("p['tot_invoice']"), None, self.pd_cell_style_decimal],
                'totals': [1, 23, 'number', _render("p['tot_invoice']"), None, self.rt_cell_style_decimal]},
            'amount_residual': {
                'header': [1, 23, 'text', _render("_('Sisa')")],
                'lines': [1, 0, 'number', _render("p['amount_residual']"), None, self.pd_cell_style_decimal],
                'totals': [1, 23, 'number', _render("p['amount_residual']"), None, self.rt_cell_style_decimal]},
            'current': {
                'header': [1, 23, 'text', _render("_('Current')")],
                'lines': [1, 0, 'number', _render("p['current']"), None, self.pd_cell_style_decimal],
                'totals': [1, 23, 'number', _render("p['current']"), None, self.rt_cell_style_decimal]},
            # 'overdue_1_30': {
            #     'header': [1, 23, 'text', _render("_('Overdue 1 - 30')")],
            #     'lines': [1, 0, 'number', _render("p['overdue_1_30']"), None, self.pd_cell_style_decimal],
            #     'totals': [1, 23, 'number', _render("p['overdue_1_30']"), None, self.rt_cell_style_decimal]},
            # 'overdue_31_60': {
            #     'header': [1, 23, 'text', _render("_('Overdue 31 - 60')")],
            #     'lines': [1, 0, 'number', _render("p['overdue_31_60']"), None, self.pd_cell_style_decimal],
            #     'totals': [1, 23, 'number', _render("p['overdue_31_60']"), None, self.rt_cell_style_decimal]},
            # 'overdue_61_90': {
            #     'header': [1, 23, 'text', _render("_('Overdue 61 - 90')")],
            #     'lines': [1, 0, 'number', _render("p['overdue_61_90']"), None, self.pd_cell_style_decimal],
            #     'totals': [1, 23, 'number', _render("p['overdue_61_90']"), None, self.rt_cell_style_decimal]},
            # 'overdue_91_n': {
            #     'header': [1, 23, 'text', _render("_('Overdue > 90')")],
            #     'lines': [1, 0, 'number', _render("p['overdue_91_n']"), None, self.pd_cell_style_decimal],
            #     'totals': [1, 23, 'number', _render("p['overdue_91_n']"), None, self.rt_cell_style_decimal]},
            'reference': {
                'header': [1, 23, 'text', _render("_('Ref')")],
                'lines': [1, 0, 'text', _render("p['reference']")],
                'totals': [1, 23, 'text', None]},
            'journal_name': {
                'header': [1, 23, 'text', _render("_('Scr')")],
                'lines': [1, 0, 'text', _render("p['journal_name']")],
                'totals': [1, 23, 'text', None]},
            'first_date': {
                'header': [1, 23, 'text', _render("_('First Date')")],
                'lines': [1, 0, 'text', _render("p['first_date']")],
                'totals': [1, 23, 'text', None]},
            'last_date': {
                'header': [1, 23, 'text', _render("_('Last Date')")],
                'lines': [1, 0, 'text', _render("p['last_date']")],
                'totals': [1, 23, 'text', None]},
            'id_aml': {
                'header': [1, 23, 'text', _render("_('ID AML')")],
                'lines': [1, 0, 'text', _render("p['id_aml']")],
                'totals': [1, 23, 'text', None]},
        }
        # XLS Template
        self.col_specs_template_details = {
            
        }

    # def get_balance(self, cr, uid, ids, date_query, date_query_params, context=None):
    #     mapping = {
    #         'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
    #         'debit': "COALESCE(SUM(l.debit), 0) as debit",
    #         'credit': "COALESCE(SUM(l.credit), 0) as credit",
    #         'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
    #     }
    #     children_and_consolidated = self.pool.get('account.account')._get_children_and_consol(cr, uid, ids, context=context)
    #     accounts = {}
    #     res = {}
    #     if children_and_consolidated:
    #         aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

    #         wheres = [""]
    #         if date_query.strip():
    #             wheres.append(date_query.strip())
    #         if aml_query.strip():
    #             wheres.append(aml_query.strip())
    #         filters = " AND ".join(wheres)
    #         request = ("SELECT l.account_id as id, " +\
    #                    ', '.join(mapping.values()) +
    #                    " FROM account_move_line l" \
    #                    " WHERE l.account_id IN %s " \
    #                         + filters +
    #                    " GROUP BY l.account_id")
    #         params = (tuple(children_and_consolidated),) + date_query_params
    #         cr.execute(request, params)

    #         for row in cr.dictfetchall():
    #             accounts[row['id']] = row

    #         children_and_consolidated.reverse()
    #         brs = list(self.pool.get('account.account').browse(cr, uid, children_and_consolidated, context=context))
    #         sums = {}
    #         currency_obj = self.pool.get('res.currency')
    #         while brs:
    #             current = brs.pop(0)
    #             if accounts.get(current.id, {}).get('balance', 0.0) != 0:
    #                 sums[current] = accounts.get(current.id, {}).get('balance', 0.0)
    #                 for child in current.child_id:
    #                     if child.company_id.currency_id.id == current.company_id.currency_id.id:
    #                         sums[current] += sums[child]
    #                     else:
    #                         sums[current] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child], context=context)
    #                 if current.currency_id and current.exchange_rate and \
    #                             ('adjusted_balance' in ['balance'] or 'unrealized_gain_loss' in ['balance']):
    #                     adj_bal = sums[current].get('foreign_balance', 0.0) / current.exchange_rate
    #                     sums[current].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current].get('balance', 0.0)})
    #     return sums

    def generate_xls_report(self, _p, _xs, data, objects, wb):
        wanted_list_overview = _p.wanted_list_overview
        wanted_list_details = _p.wanted_list_details
        self.col_specs_template_overview.update(_p.template_update_overview)
        self.col_specs_template_details.update(_p.template_update_details)
        _ = _p._

        for r in _p.reports:
            title_short = r['title_short'].replace('/', '-')
            ws_o = wb.add_sheet(title_short)
           
            for ws in [ws_o]:
                ws.panes_frozen = True
                ws.remove_splits = True
                ws.portrait = 0  # Landscape
                ws.fit_width_to_pages = 1
            row_pos_o = 0
            row_pos_d = 0

            # set print header/footer
            for ws in [ws_o]:
                ws.header_str = self.xls_headers['standard']
                ws.footer_str = self.xls_footers['standard']

            # Title
            ## Company ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_p.company.name, r['title'],
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Text + Tgl ##
            cell_style = xlwt.easyxf(_xs['xls_title'])
            report_name = ' '.join(
                [_('LAPORAN CASH FLOW Per Tanggal'), _(str(datetime.today().date())),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            
            ## Start Date & End Date ##
            cell_style = xlwt.easyxf(_xs['left'])
            report_name = ' '.join(
                [_('Tanggal'), _('-' if data['start_date'] == False else str(data['start_date'])), _('s/d'), _('-' if data['end_date'] == False else str(data['end_date'])),
                 _p.report_info])
            c_specs_o = [
                ('report_name', 1, 0, 'text', report_name),
            ]
            row_data = self.xls_row_template(c_specs_o, ['report_name'])
            row_pos_o = self.xls_write_row(
                ws_o, row_pos_o, row_data, row_style=cell_style)
            row_pos_o += 1

            first_date = datetime.strptime(_p.reports[0]['ids_aml'][0]['first_date'], '%Y-%m-%d')
            last_date = datetime.strptime(_p.reports[0]['ids_aml'][0]['last_date'], '%Y-%m-%d')
            date_diff = int((datetime.date(last_date)-datetime.date(first_date)).days)
            if r['status'] == 'reconciled':
                record = {}
                for p in r['ids_aml']:
                    c_specs_o = map(lambda x: self.render(x, self.col_specs_template_overview, 'lines'),wanted_list_overview)
                    aml_id = int(c_specs_o[21][4])
                    move_brw = self.pool.get('account.move.line').browse(self.cr, SUPERUSER_ID, [aml_id])
                    key = move_brw.account_id.id
                    if key not in record:
                        per_bank = {}
                        per_bank['bank'] = move_brw.account_id
                        # bank_balances = self.get_balance(self.cr, self.uid, [move_brw.account_id.id], 'date < %s', (first_date.strftime('%Y-%m-%d'), ))
                        bank_balances = self.pool.get('account.account').browse(self.cr, self.uid, move_brw.account_id.id, context={'date_from':first_date,'date_to':first_date, 'initial_bal': True}).balance
                        per_bank['balance'] = bank_balances
                        per_bank['accounts'] = {}
                        record[key] = per_bank
                    for line in move_brw.move_id.line_id:
                        if line.id == aml_id or not line.reconcile_id:
                            continue
                        value_in = 0
                        value_out = 0
                        if move_brw.debit > 0:
                            value_in = line.credit
                        if move_brw.credit > 0:
                            value_out = line.debit
                        per_account = {}
                        per_account['in'] = value_in
                        per_account['out'] = value_out
                        per_account['name'] = line.account_id.name
                        if line.account_id.code[:5] not in record[key]['accounts']:
                            record[key]['accounts'][line.account_id.code[:5]] = per_account
                        else:
                            record[key]['accounts'][line.account_id.code[:5]]['in'] += value_in
                            record[key]['accounts'][line.account_id.code[:5]]['out'] += value_out
                current_bank_account = False
                row_data_begin_review = 0

                for res in record:
                    row_pos_o += 2
                    c_specs_o = []
                    c_specs_o.append(['accounts', 1, 23, 'text', record[res]['bank'].name])
                    c_specs_o.append(['in', 1, 23, 'text', 'In'])
                    c_specs_o.append(['out', 1, 23, 'text', 'Out'])
                    c_specs_o.append(['saldo', 1, 23, 'text', 'Saldo'])
                    row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                    row_pos_o = self.xls_write_row(
                        ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                        set_column_size=True)

                    row_data_begin_review = row_pos_o

                    c_specs_o = []
                    c_specs_o.append(['accounts', 1, 0, 'text', 'Saldo Awal '+first_date.strftime('%Y-%m-%d')])
                    c_specs_o.append(['in', 1, 0, 'number', 0, None, self.pd_cell_style_decimal])
                    c_specs_o.append(['out', 1, 0, 'number', 0, None, self.pd_cell_style_decimal])
                    c_specs_o.append(['saldo', 1, 0, 'number', record[res]['balance'], None, self.pd_cell_style_decimal])
                    row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                    row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style,set_column_size=True)
                    for acc in record[res]['accounts']:
                        c_specs_o = []
                        c_specs_o.append(['accounts', 1, 0, 'text', acc + ' - ' + record[res]['accounts'][acc]['name']])
                        c_specs_o.append(['in', 1, 0, 'number', record[res]['accounts'][acc]['in'], None, self.pd_cell_style_decimal])
                        c_specs_o.append(['out', 1, 0, 'number', record[res]['accounts'][acc]['out'], None, self.pd_cell_style_decimal])
                        row_data = self.xls_row_template(
                            c_specs_o, [x[0] for x in c_specs_o])
                        row_pos_o = self.xls_write_row(
                            ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                        ws_o.write(row_pos_o-1, 3, xlwt.Formula("SUM(D"+str(row_pos_o-1)+",B"+str(row_pos_o)+",-C"+str(row_pos_o)+")"), self.pd_cell_style_decimal)
                        
                    row_data_end_review = row_pos_o
                    ws_o.write(row_pos_o, 0, 'Saldo Akhir '+last_date.strftime('%Y-%m-%d'), self.ph_cell_style)
                    ws_o.write(row_pos_o, 1, xlwt.Formula("SUM(B"+str(row_data_begin_review+1)+":B"+str(row_data_end_review)+")"), self.rt_cell_style_decimal)
                    ws_o.write(row_pos_o, 2, xlwt.Formula("SUM(C"+str(row_data_begin_review+1)+":C"+str(row_data_end_review)+")"), self.rt_cell_style_decimal)
                    ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin_review+1)+",B"+str(row_data_end_review+1)+",-C"+str(row_data_end_review+1)+")"), self.rt_cell_style_decimal)

            if r['status'] == 'outstanding':
                ## Piutang ##
                cell_style = xlwt.easyxf(_xs['xls_title'])
                report_name = ' '.join(
                    [_('PIUTANG'),
                     _p.report_info])
                c_specs_o = [
                    ('report_name', 1, 0, 'text', report_name),
                ]
                row_data = self.xls_row_template(c_specs_o, ['report_name'])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=cell_style)
                # Report Column Headers
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'header',
                        render_space={'_': _p._}),
                    wanted_list_overview)
                c_specs_o.pop(21)
                c_specs_o.pop(20)
                c_specs_o.pop(19)
                c_specs_o.pop(5)
                c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 23, 'text', '<'+first_date.strftime('%Y-%m-%d')])
                for i in range(date_diff+1):
                    c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 23, 'text', (first_date+timedelta(days=i)).strftime('%Y-%m-%d')])
                c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 23, 'text', '>'+last_date.strftime('%Y-%m-%d')])
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                    set_column_size=True)
                # ws_o.set_horz_split_pos(row_pos_o)
                
                row_data_begin_ar = row_pos_o
                
                # Columns and Rows
                no = 0
                for p in r['ids_aml']:
                    c_specs_o = map(
                        lambda x: self.render(
                            x, self.col_specs_template_overview, 'lines'),
                        wanted_list_overview)
                    if c_specs_o[5][4] == 'receivable':
                        if c_specs_o[11][4] < first_date.strftime('%Y-%m-%d'):
                            c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 0, 'number', c_specs_o[15][4], None, self.pd_cell_style_decimal])
                        else:
                            c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 0, 'number', 0.0, None, self.pd_cell_style_decimal])
                        for i in range(date_diff+1):
                            if c_specs_o[11][4] == (first_date+timedelta(days=i)).strftime('%Y-%m-%d'):
                                c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 0, 'number', c_specs_o[15][4], None, self.pd_cell_style_decimal])
                            else:
                                c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 0, 'number', 0.0, None, self.pd_cell_style_decimal])
                        if c_specs_o[11][4] > last_date.strftime('%Y-%m-%d'):
                            c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 0, 'number', c_specs_o[15][4], None, self.pd_cell_style_decimal])
                        else:
                            c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 0, 'number', 0.0, None, self.pd_cell_style_decimal])
                        for x in c_specs_o :
                            if x[0] == 'no' :
                                no += 1
                                x[4] = no
                        c_specs_o.pop(21)
                        c_specs_o.pop(20)
                        c_specs_o.pop(19)
                        c_specs_o.pop(5)
                        row_data = self.xls_row_template(
                            c_specs_o, [x[0] for x in c_specs_o])
                        row_pos_o = self.xls_write_row(ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                
                row_data_end_ar = row_pos_o

                # Totals
                ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)
                ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin_ar)+":N"+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin_ar)+":O"+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin_ar)+":P"+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 17, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin_ar)+":S"+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                i = False
                for i in range(date_diff+1):
                    div=i+20
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+19, xlwt.Formula("SUM("+string+str(row_data_begin_ar)+":"+string+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                if i:
                    div=i+21
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+20, xlwt.Formula("SUM("+string+str(row_data_begin_ar)+":"+string+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                else:
                    ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin_ar)+":T"+str(row_data_end_ar)+")"), self.rt_cell_style_decimal)
                    
                row_pos_o += 4

                ## Hutang ##
                cell_style = xlwt.easyxf(_xs['xls_title'])
                report_name = ' '.join(
                    [_('HUTANG'),
                     _p.report_info])
                c_specs_o = [
                    ('report_name', 1, 0, 'text', report_name),
                ]
                row_data = self.xls_row_template(c_specs_o, ['report_name'])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=cell_style)
                # Report Column Headers
                c_specs_o = map(
                    lambda x: self.render(
                        x, self.col_specs_template_overview, 'header',
                        render_space={'_': _p._}),
                    wanted_list_overview)
                c_specs_o.pop(21)
                c_specs_o.pop(20)
                c_specs_o.pop(19)
                c_specs_o.pop(5)
                c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 23, 'text', '<'+first_date.strftime('%Y-%m-%d')])
                for i in range(date_diff+1):
                    c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 23, 'text', (first_date+timedelta(days=i)).strftime('%Y-%m-%d')])
                c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 23, 'text', '>'+last_date.strftime('%Y-%m-%d')])
                row_data = self.xls_row_template(
                    c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                    set_column_size=True)
                # ws_o.set_horz_split_pos(row_pos_o)
                
                row_data_begin_ap = row_pos_o

                # Columns and Rows
                no = 0
                for p in r['ids_aml']:
                    c_specs_o = map(
                        lambda x: self.render(
                            x, self.col_specs_template_overview, 'lines'),
                        wanted_list_overview)
                    if c_specs_o[5][4] == 'payable':
                        if c_specs_o[11][4] < first_date.strftime('%Y-%m-%d'):
                            c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 0, 'number', c_specs_o[15][4], None, self.pd_cell_style_decimal])
                        else:
                            c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 0, 'number', 0.0, None, self.pd_cell_style_decimal])
                        for i in range(date_diff+1):
                            if c_specs_o[11][4] == (first_date+timedelta(days=i)).strftime('%Y-%m-%d'):
                                c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 0, 'number', c_specs_o[15][4], None, self.pd_cell_style_decimal])
                            else:
                                c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 0, 'number', 0.0, None, self.pd_cell_style_decimal])
                        if c_specs_o[11][4] > last_date.strftime('%Y-%m-%d'):
                            c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 0, 'number', c_specs_o[15][4], None, self.pd_cell_style_decimal])
                        else:
                            c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 0, 'number', 0.0, None, self.pd_cell_style_decimal])
                        for x in c_specs_o :
                            if x[0] == 'no' :
                                no += 1
                                x[4] = no
                        c_specs_o.pop(21)
                        c_specs_o.pop(20)
                        c_specs_o.pop(19)
                        c_specs_o.pop(5)
                        row_data = self.xls_row_template(
                            c_specs_o, [x[0] for x in c_specs_o])
                        row_pos_o = self.xls_write_row(
                            ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                
                row_data_end_ap = row_pos_o

                # Totals
                ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)
                ws_o.write(row_pos_o, 2, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 3, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 4, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 5, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 6, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 7, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 8, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 9, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 10, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 11, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 12, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 13, xlwt.Formula("SUM(N"+str(row_data_begin_ap)+":N"+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 14, xlwt.Formula("SUM(O"+str(row_data_begin_ap)+":O"+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 15, xlwt.Formula("SUM(P"+str(row_data_begin_ap)+":P"+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 16, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 17, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 18, xlwt.Formula("SUM(S"+str(row_data_begin_ap)+":S"+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)
                i = False
                for i in range(date_diff+1):
                    div=i+20
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+19, xlwt.Formula("SUM("+string+str(row_data_begin_ap)+":"+string+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)
                if i:
                    div=i+21
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+20, xlwt.Formula("SUM("+string+str(row_data_begin_ap)+":"+string+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)
                else:
                    ws_o.write(row_pos_o, 19, xlwt.Formula("SUM(T"+str(row_data_begin_ap)+":T"+str(row_data_end_ap)+")"), self.rt_cell_style_decimal)

                row_pos_o += 4

                ## Bank ##
                cell_style = xlwt.easyxf(_xs['xls_title'])
                report_name = ' '.join(
                    [_('Saldo Bank Per Tanggal'), _(str(first_date.strftime('%Y-%m-%d'))),
                     _p.report_info])
                c_specs_o = [
                    ('report_name', 1, 0, 'text', report_name),
                ]
                row_data = self.xls_row_template(c_specs_o, ['report_name'])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=cell_style)
                # Report Column Headers
                c_specs_o = []
                c_specs_o.append(['no', 1, 23, 'text', 'No'])
                c_specs_o.append(['account_bank', 1, 23, 'text', 'Bank / Cash'])
                c_specs_o.append(['balance', 1, 23, 'text', 'Balance'])
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                    set_column_size=True)
                # ws_o.set_horz_split_pos(row_pos_o)
                
                row_data_begin_bank = row_pos_o

                # Columns and Rows
                no = 0
                search_ids = self.pool.get('dym.cash.flow.report').search(self.cr, self.uid, [], order='id desc', limit=1)
                bank_ids = self.pool.get('dym.cash.flow.report').browse(self.cr, self.uid, search_ids).bank_ids
                if len(bank_ids) == 0 :
                    bank_src = self.pool.get('account.account').search(self.cr, self.uid, [('user_type.code','in',['bank','cash'])])
                    bank_ids = self.pool.get('account.account').browse(self.cr, self.uid, bank_src)
                # bank_balances = self.get_balance(self.cr, self.uid, [x.id for x in bank_ids], 'date < %s', (first_date.strftime('%Y-%m-%d'), ))
                for bank in bank_ids:
                    no += 1
                    # balance = 0
                    # if bank in bank_balances:
                    #     balance = bank_balances[bank]
                    balance = self.pool.get('account.account').browse(self.cr, self.uid, bank.id, context={'date_from':first_date,'date_to':first_date, 'initial_bal': True}).balance
                    c_specs_o = []
                    c_specs_o.append(['no', 1, 0, 'number', no])
                    c_specs_o.append(['account_bank', 1, 0, 'text', bank.name])
                    c_specs_o.append(['balance', 1, 0, 'number', balance, None, self.pd_cell_style_decimal])
                    row_data = self.xls_row_template(
                        c_specs_o, [x[0] for x in c_specs_o])
                    row_pos_o = self.xls_write_row(
                        ws_o, row_pos_o, row_data, row_style=self.pd_cell_style)
                
                row_data_end_bank = row_pos_o

                # Totals
                ws_o.write(row_pos_o, 0, None, self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 1, 'Totals', self.ph_cell_style)
                ws_o.write(row_pos_o, 2, xlwt.Formula("SUM(C"+str(row_data_begin_bank)+":C"+str(row_data_end_bank)+")"), self.rt_cell_style_decimal)
                

                row_pos_o += 4
                
                ## Summary ##
                cell_style = xlwt.easyxf(_xs['xls_title'])
                report_name = ' '.join(
                    [_('Summary Cash Flow'),
                     _p.report_info])
                c_specs_o = [
                    ('report_name', 1, 0, 'text', report_name),
                ]
                row_data = self.xls_row_template(c_specs_o, ['report_name'])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=cell_style)
                # Report Column Headers
                c_specs_o = []
                c_specs_o.append(['type', 1, 23, 'text', ''])
                c_specs_o.append(['saldo', 1, 23, 'text', 'Saldo'])
                c_specs_o.append(['<'+first_date.strftime('%Y-%m-%d'), 1, 23, 'text', '<'+first_date.strftime('%Y-%m-%d')])
                for i in range(date_diff+1):
                    c_specs_o.append([(first_date+timedelta(days=i)).strftime('%Y-%m-%d'), 1, 23, 'text', (first_date+timedelta(days=i)).strftime('%Y-%m-%d')])
                c_specs_o.append(['>'+last_date.strftime('%Y-%m-%d'), 1, 23, 'text', '>'+last_date.strftime('%Y-%m-%d')])
                row_data = self.xls_row_template(c_specs_o, [x[0] for x in c_specs_o])
                row_pos_o = self.xls_write_row(
                    ws_o, row_pos_o, row_data, row_style=self.rh_cell_style,
                    set_column_size=True)

                row_data_begin_summary = row_pos_o
                
                ws_o.write(row_pos_o, 0, 'AR', self.ph_cell_style)
                div=date_diff+21
                string=""
                temp=0
                while div>0:
                    module=(div-1)%26
                    string=chr(65+module)+string
                    div=int((div-module)/26)
                ws_o.write(row_pos_o, 1, xlwt.Formula("SUM(S"+str(row_data_end_ar+1)+":"+string+str(row_data_end_ar+1)+")"), self.rt_cell_style_decimal)    
                ws_o.write(row_pos_o, 2, xlwt.Formula("S"+str(row_data_end_ar+1)), self.rt_cell_style_decimal)    
                i = False
                for i in range(date_diff+1):
                    div=i+20
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+3, xlwt.Formula(string+str(row_data_end_ar+1)), self.rt_cell_style_decimal)       

                if i:
                    div=i+21
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+4, xlwt.Formula(string+str(row_data_end_ar+1)), self.rt_cell_style_decimal) 
                else:
                    ws_o.write(row_pos_o, 3, xlwt.Formula("T"+str(row_data_end_ar+1)), self.rt_cell_style_decimal)   

                row_pos_o += 1
                ws_o.write(row_pos_o, 0, 'AP', self.ph_cell_style)
                div=date_diff+21
                string=""
                temp=0
                while div>0:
                    module=(div-1)%26
                    string=chr(65+module)+string
                    div=int((div-module)/26)
                ws_o.write(row_pos_o, 1, xlwt.Formula("SUM(S"+str(row_data_end_ap+1)+":"+string+str(row_data_end_ap+1)+")"), self.rt_cell_style_decimal)    
                ws_o.write(row_pos_o, 2, xlwt.Formula("S"+str(row_data_end_ap+1)), self.rt_cell_style_decimal)    
                i = False
                for i in range(date_diff+1):
                    div=i+20
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+3, xlwt.Formula(string+str(row_data_end_ap+1)), self.rt_cell_style_decimal)       

                if i:
                    div=i+21
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+4, xlwt.Formula(string+str(row_data_end_ap+1)), self.rt_cell_style_decimal) 
                else:
                    ws_o.write(row_pos_o, 3, xlwt.Formula("T"+str(row_data_end_ap+1)), self.rt_cell_style_decimal) 

                row_data_end_summary_ar_ap = row_pos_o

                row_pos_o += 1
                ws_o.write(row_pos_o, 0, 'CIF (COF)', self.ph_cell_style)
                ws_o.write(row_pos_o, 1, xlwt.Formula("SUM(B"+str(row_data_begin_summary+1)+":B"+str(row_data_end_summary_ar_ap+1)+")"), self.rt_cell_style_decimal)    
                ws_o.write(row_pos_o, 2, xlwt.Formula("SUM(C"+str(row_data_begin_summary+1)+":C"+str(row_data_end_summary_ar_ap+1)+")"), self.rt_cell_style_decimal)  
                i = False
                for i in range(date_diff+1):
                    div=i+4
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+3, xlwt.Formula("SUM("+string+str(row_data_begin_summary+1)+":"+string+str(row_data_end_summary_ar_ap+1)+")"), self.rt_cell_style_decimal)        
                if i:
                    div=i+5
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+4, xlwt.Formula("SUM("+string+str(row_data_begin_summary+1)+":"+string+str(row_data_end_summary_ar_ap+1)+")"), self.rt_cell_style_decimal) 
                else:
                    ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(D"+str(row_data_begin_summary+1)+":D"+str(row_data_end_summary_ar_ap+1)+")"), self.rt_cell_style_decimal)  

                row_pos_o += 1
                ws_o.write(row_pos_o, 0, 'Bank', self.ph_cell_style)
                ws_o.write(row_pos_o, 1, xlwt.Formula("C"+str(row_data_end_bank+1)), self.rt_cell_style_decimal)
                ws_o.write(row_pos_o, 2, xlwt.Formula("SUM(B"+str(row_data_end_summary_ar_ap+3)+",C"+str(row_data_end_summary_ar_ap+2)+")"), self.rt_cell_style_decimal)  
                i = False
                for i in range(date_diff+1):
                    div=i+4
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)  
                    div=i+3
                    prev_total=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        prev_total=chr(65+module)+prev_total
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+3, xlwt.Formula("SUM("+prev_total+str(row_data_end_summary_ar_ap+3)+","+string+str(row_data_end_summary_ar_ap+2)+")"), self.rt_cell_style_decimal)    

                if i:
                    div=i+5
                    string=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        string=chr(65+module)+string
                        div=int((div-module)/26)
                    div=i+4
                    prev_total=""
                    temp=0
                    while div>0:
                        module=(div-1)%26
                        prev_total=chr(65+module)+prev_total
                        div=int((div-module)/26)
                    ws_o.write(row_pos_o, i+4, xlwt.Formula("SUM("+prev_total+str(row_data_end_summary_ar_ap+3)+","+string+str(row_data_end_summary_ar_ap+2)+")"), self.rt_cell_style_decimal) 
                else:
                    ws_o.write(row_pos_o, 3, xlwt.Formula("SUM(C"+str(row_data_end_summary_ar_ap+3)+",D"+str(row_data_end_summary_ar_ap+2)+")"), self.rt_cell_style_decimal)  

            # Footer
            ws_o.write(row_pos_o + 1, 0, None)
            ws_o.write(row_pos_o + 2, 0, _p.report_date + ' ' + str(self.pool.get('res.users').browse(self.cr, self.uid, self.uid).name))

report_cash_flow_xls('report.Laporan Cash Flow', 'account.move.line', parser = dym_report_cash_flow_print_xls)
