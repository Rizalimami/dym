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

class dym_titipan_customer_report_print(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        if context is None:
            context = {}
        super(dym_titipan_customer_report_print, self).__init__(
            cr, uid, name, context=context)
        self.context = context
        self.localcontext.update({
            'formatLang_zero2blank': self.formatLang_zero2blank,
            })

    def set_context(self, objects, data, ids, report_type=None):
        cr = self.cr
        uid = self.uid
        context = self.context
        start_date = data['start_date']
        end_date = data['end_date']
        branch_ids = data['branch_ids']
        titipan = data['titipan']
        jns_titipan = titipan[8:]
        title_prefix = ''
        title_short_prefix = ''
        report_titipan_customer = {
            'type': 'payable',
            'title': '',
            'title_short': title_short_prefix + ', ' + _('Laporan Titipan')}

        user_brw = self.pool.get('res.users').browse(cr, uid, uid)
        user_branch_type = user_brw.branch_type

        query_end_ac_code=""
        query_end_branch=""
        query_end_date=""

        if titipan != '2105002 Titipan STNK' :
            query_end_ac_code +=" AND ac.code = '%s' " % str(titipan)[:7]
        if titipan == '2105002 Titipan STNK' :
            if start_date :
                query_end_date +=" AND dso.date_order >= '%s'" % str(start_date)
            if end_date :
                query_end_date +=" AND dso.date_order <= '%s'" % str(end_date)
        else:
            if start_date :
                query_end_date +=" AND am.date >= '%s'" % str(start_date)
            if end_date :
                query_end_date +=" AND am.date <= '%s'" % str(end_date)
        if branch_ids :
            query_end_branch +=" AND db.id in %s" % str(tuple(branch_ids)).replace(',)', ')')
        else:
            query_end_branch = ""

        query_ttp_stnk = """SELECT  distinct db.name as cabang,
            db.code as branch_id,
            dso.division as divisi,
            dso.date_order as tgl_input,
            dso.name as id_ai,
            res.default_code as kode_customer,
            trim(res.name) as nama_customer,
            aj.name as payment_method,
            ac.code as code,
            ac.code || '-' ||ac.name as account,
            spl.name as description,
            --coalesce(dso.amount_bbn,0) as nilai_titipan,
            case when av_cde.am_name is not null then coalesce(dso.amount_bbn,0) + coalesce(av_cde.aml_credit,0) else coalesce(dso.amount_bbn,0) end as nilai_titipan,
            aac.code || '-' || aac.name as account_analytic,
            dpb.name as journal_item,
            null as tgl_alokasi,
            0 as nilai_alokasi,
            0 as total_tagihan,
            0 as total_jasa,
            0 as selisih_margin,
            0 as sisa_titipan,
            dpb.id as dpb_id,
            dpbl.id as dpbl_id,
            av_cde.am_id as am_id,
            dso.id as id,
            drj.id as drj_id,
            ai.id as sin_id,
            case when av_cde.aml_partner_id is not null then coalesce(av_cde.aml_credit,0) else 0 end as pajak_progresif_cde,
            coalesce(nde_s.amount,0) as pajak_progresif_nde,
            case when av_cde.aml_credit is null and nde_s.amount is null then 0
                else case when av_cde.aml_credit != nde_s.amount and av_cde.aml_credit is not null and nde_s.amount is not null then nde_s.amount
                else case when av_cde.aml_credit is not null and nde_s.amount is null then av_cde.aml_credit
            else nde_s.amount end end end as pajak_progresif
            from    account_move_line aml 
            left join account_move am on aml.move_id = am.id 
            left join account_invoice ai on am.name = ai.origin 
            left join account_invoice_line ail on ail.invoice_id = ai.id 
            left join dealer_sale_order dso on am.ref = dso.name
            left join dealer_sale_order_line dsol on dso.id = dsol.dealer_sale_order_line_id and dsol.is_bbn in ('Y')
            left join dym_branch db on dso.branch_id = db.id
            left join res_partner res on dso.partner_id = res.id
            left join stock_production_lot spl on dsol.lot_id = spl.id
            left join dym_proses_birojasa_line dpbl on dpbl.name = spl.id
            left join dym_proses_birojasa dpb on dpb.id = dpbl.proses_biro_jasa_id --and dpb.state in ('done','approved')
            left join account_journal aj on aml.journal_id = aj.id
            left join account_account ac on aml.account_id = ac.id
            left join account_analytic_account aac on aml.analytic_account_id =  aac.id
            left join dym_retur_jual drj on drj.dso_id = dso.id and drj.state in ('approved','done')
            left join (select am.id as am_id, am.name as am_name, aml.name as aml_name, aml.partner_id as aml_partner_id, aml.credit as aml_credit
                        from account_move_line aml 
                        left join account_move am on aml.move_id = am.id
                        left join account_account ac on aml.account_id = ac.id
                        where ac.code in ('2105002') and aml.name like ('%PAJAK PROGRESIF%') and left(am.name,3) = 'CDE' and length(am.name) = 22) av_cde on av_cde.aml_partner_id = res.id
            left join (select ai.id, 
                        ai.number as nde_s, 
                        substring(ai.name from 22 for (position(''',' in ai.name) - 22)) as name,
                        substring(ai.name from (position('e ''' in ai.name)+3) for 12) as nosin,  
                        --ai.name as keterangan, 
                        ai.origin as tbj_no, 
                        dpb.state as tbj_state,
                        ai.state as state, 
                        ai.date_invoice as date, 
                        coalesce(ai.amount_total,0) as amount, 
                        rp.id || ' - ' || rp.name, 
                        ai.commercial_partner_id, 
                        rp_qq.id || ' - ' || rp_qq.name,
                        --ai.journal_id,
                        --ai.move_id, 
                        aa.code || ' - ' || aa.name as account,
                        db.id || ' - ' || db.name as branch
                        from account_invoice ai
                        left join account_account aa on aa.id = ai.account_id
                        left join dym_branch db on db.id = ai.branch_id
                        left join res_partner rp on rp.id = ai.partner_id
                        left join res_partner rp_qq on rp_qq.id = ai.qq_id
                        left join dym_proses_birojasa dpb on dpb.name = ai.origin
                        where left(ai.number,5) = 'NDE-S' 
                        and ai.name like 'Pajak Progresif%'
                        and ai.state not in ('draft','cancel')
                        and dpb.state in ('approved','done')) nde_s on nde_s.nosin = spl.name and trim(nde_s.name) = trim(res.name)
            --where dso.state in ('done','progress') and aml.account_id = 2511 
            --and dpb.state in ('done','approved') 
            where dso.state in ('done','progress') and ac.code in ('2105002')
            """

        query_ttp_stnk_opbal = """union 
            SELECT  distinct db.name as cabang,
                db.code as branch_id,
                aml.division as divisi,
                am.date as tgl_input,
                am.name as id_ai,
                res.default_code as kode_customer,
                trim(res.name) as nama_customer,
                aj.name as payment_method,
                ac.code as code,
                ac.code || '-' ||ac.name as account,
                spl.name as description,
                aml.credit as nilai_titipan,
                aac.code || '-' || aac.name as account_analytic,
                dpb.name as journal_item,
                null as tgl_alokasi,
                0 as nilai_alokasi,
                0 as total_tagihan,
                0 as total_jasa,
                0 as selisih_margin,
                0 as sisa_titipan,                
                dpb.id as dpb_id,
                dpbl.id as dpbl_id,
                am.id as am_id,
                aml.id as id,
                0 as drj_id,
                ai.id as sin_id,
                case when av_cde.aml_partner_id is not null then coalesce(av_cde.aml_credit,0) else 0 end as pajak_progresif_cde,
                coalesce(nde_s.amount,0) as pajak_progresif_nde,
                case when av_cde.aml_credit is null and nde_s.amount is null then 0
                    else case when av_cde.aml_credit != nde_s.amount and av_cde.aml_credit is not null and nde_s.amount is not null then nde_s.amount
                    else case when av_cde.aml_credit is not null and nde_s.amount is null then av_cde.aml_credit
                else nde_s.amount end end end as pajak_progresif
                from    account_move_line aml 
                left join account_move am on aml.move_id = am.id 
                left join account_invoice ai on am.name = ai.origin 
                left join account_invoice_line ail on ail.invoice_id = ai.id 
                left join stock_production_lot spl on spl.name = right(aml.name,12)
                left join dym_proses_birojasa_line dpbl on dpbl.name = spl.id
                left join dym_proses_birojasa dpb on dpb.id = dpbl.proses_biro_jasa_id
                left join account_journal aj on aml.journal_id = aj.id
                left join account_account ac on aml.account_id = ac.id
                left join account_analytic_account aac on ail.account_analytic_id =  aac.id
                left join dym_branch db on aml.branch_id = db.id
                left join res_partner res on aml.partner_id = res.id
                left join account_invoice ai2 on dpb.name = ai2.origin
                left join account_move am2 on am2.name = ai2.number
                left join (select rp.name as name, aml.partner_id as aml_partner_id, sum(aml.credit) as aml_credit
                            from account_move_line aml 
                            left join account_move am on aml.move_id = am.id
                            left join account_account ac on aml.account_id = ac.id
                            left join res_partner rp on rp.id = aml.partner_id
                            where ac.code in ('2105002') and left(am.name,3) = 'CDE' and length(am.name) = 22
                            group by rp.name, aml.partner_id) av_cde on av_cde.aml_partner_id = res.id
                left join (select ai.id, 
                            ai.number as nde_s, 
                            substring(ai.name from 22 for (position(''',' in ai.name) - 22)) as name,
                            substring(ai.name from (position('e ''' in ai.name)+3) for 12) as nosin,  
                            --ai.name as keterangan, 
                            ai.origin as tbj_no, 
                            dpb.state as tbj_state,
                            ai.state as state, 
                            ai.date_invoice as date, 
                            coalesce(ai.amount_total,0) as amount, 
                            rp.id || ' - ' || rp.name, 
                            ai.commercial_partner_id, 
                            rp_qq.id || ' - ' || rp_qq.name,
                            --ai.journal_id,
                            --ai.move_id, 
                            aa.code || ' - ' || aa.name as account,
                            db.id || ' - ' || db.name as branch
                            from account_invoice ai
                            left join account_account aa on aa.id = ai.account_id
                            left join dym_branch db on db.id = ai.branch_id
                            left join res_partner rp on rp.id = ai.partner_id
                            left join res_partner rp_qq on rp_qq.id = ai.qq_id
                            left join dym_proses_birojasa dpb on dpb.name = ai.origin
                            where left(ai.number,5) = 'NDE-S' 
                            and ai.name like 'Pajak Progresif%'
                            and ai.state not in ('draft','cancel')
                            and dpb.state in ('approved','done')) nde_s on nde_s.nosin = spl.name and trim(nde_s.name) = trim(res.name)
                --where   ac.code in ('2105002') and aj.id = 633 
                where   ac.code in ('2105002') and aj.id in (1317,618,1681,590,633)
            """
        
        query_ttp_um_combined_rev = """
            -- UM
            with recursive test as (
            select dd.*,res.default_code as kode_customer,
                            res.name as nama_customer,
                            aj.name as payment_method
                            from (
            select
                am.journal_id,aml.partner_id ,aml.id amild,am.id amid,db.name as cabang,
                            db.code as branch_id1,
                            aml.division as divisi,
                            am.date tgl_input,
                            am.name as id_ai,             
                            ac.code as code,
                            ac.code || '-' || ac.name as account,
                            aml.name as description,
                            coalesce(aml.credit, 0) as nilai_titipan,
                            am.name,
                            aml.credit,
                            aml.debit
            from  account_move am, 
            account_move_line aml,
            account_account ac,
            dym_branch db
            where am.id = aml.move_id
            and  left(am.name, 3) in ('CDE') and  length(am.name) < 33 and am.date >= '%s' 
            AND am.date <= '%s'
            and  aml.account_id = ac.id
            and ac.code in ('2105001')
            and aml.branch_id = db.id
            and db.id in %s) dd
            left join res_partner res on dd.partner_id = res.id
            left join account_journal aj on dd.journal_id = aj.id)
            select ff.*
            from (select dd.cabang,dd.branch_id1,dd.divisi,dd.tgl_input,id_ai,
            kode_customer,
            nama_customer,
            payment_method,
            account,
            description,
            nilai_titipan,
            account_analytic,
                            case
                            when rev.am_reverse_from_id is not null then
                            rev.am_name
                            else
                            number
                            end as journal_item,

                            case 
                            when length(dd.name) = 22 and rev.am_reverse_from_id is not null and rev.aml_date >= '%s' and rev.aml_date <= '%s' then rev.aml_date
                            else case when length(dd.name) = 22 and rev.am_reverse_from_id is null and value_date >= '%s' and value_date <= '%s' then value_date 
                            else null end end as tgl_alokasi,

                            case
                            when length(dd.name) = 22 and
                                rev.am_reverse_from_id is not null and
                                rev.aml_date >= '%s' and
                                rev.aml_date <= '%s' then
                            coalesce(rev.aml_debit, rev.aml_credit)
                            else
                            case
                            when length(dd.name) = 22 and
                                rev.am_reverse_from_id is null and
                                value_date >= '%s' and
                                value_date <= '%s' then
                            amount
                            else
                            0
                            end end as nilai_alokasi,
                            case
                            when length(dd.name) = 22 and
                                rev.am_reverse_from_id is not null and
                                rev.aml_date >= '%s' and
                                rev.aml_date <= '%s' then
                            coalesce(rev.aml_debit, rev.aml_credit) -
                            coalesce(dd.credit, 0)
                            else
                            case
                            when length(dd.name) = 32 and number is null then
                            0 - dd.debit
                            else
                            case
                            when length(dd.name) = 22 and
                                rev.am_reverse_from_id is null and
                                value_date >= '%s' and
                                value_date <= '%s' then
                            dd.credit - amount
                            else
                            case
                            when length(dd.name) = 22 and
                                rev.am_reverse_from_id is null and
                                value_date > '%s' then
                            credit - 0
                            else
                            credit - 0
                            end end end end as sisa_titipan,
                            
                            '' as dpb_id,
                            '' as dpbl_id,
                            rev.am_reverse_from_id as am_id,
                            0 as id,
                            0 as drj_id,
                            0 as sin_id,
                            number,journal_id
                    from test dd
                    left join (select avl.move_line_id, avl.voucher_id, 
                                av.number,aac.code || '-' || aac.name as account_analytic,
                av.value_date,
                avl.amount
                                from account_voucher_line avl
                                left join account_voucher av on avl.voucher_id = av.id
                                left join account_analytic_account aac on avl.account_analytic_id =
                                                                            aac.id) b on dd.amild =
                                                                                        b.move_line_id
                    left join (select am1.id              as am_id,
                                    am1.reverse_from_id as am_reverse_from_id,
                                    am1.name            as am_name,
                                    aml1.id             as aml_id,
                                    aml1.partner_id     as aml_partner_id,
                                    aml1.debit          as aml_debit,
                                    aml1.credit         as aml_credit,
                                    aml1.date           as aml_date
                                from account_move_line aml1,
                                    account_move      am1,
                                    account_account   ac1,
                                    dym_branch        db1
                                where ac1.code in ('2105001')
                                and am1.id = aml1.move_id
                                and ac1.id = aml1.account_id
                                and aml1.branch_id = db1.id
                                and db1.id in %s
                                and length(am1.name) > 32) rev on rev.am_reverse_from_id =
                                                                    dd.amid) ff
            where left(ff.number, 3) in ('CPA') or ff.number is null
            order by 1,5
        """ % (
            str(start_date),
            str(end_date),
            str(tuple(branch_ids)).replace(',)', ')'),
            str(start_date),
            str(end_date),
            str(start_date),
            str(end_date),
            str(start_date),
            str(end_date),
            str(start_date),
            str(end_date),
            str(start_date),
            str(end_date),
            str(start_date),
            str(end_date),
            str(end_date),
            str(tuple(branch_ids)).replace(',)', ')'),
        )

        query_ttp_lain = """
        --REG LAINLAIN
        SELECT db.name as cabang,
            db.code as branch_id,
            aml.id,
            aml.division as divisi,
            am.date tgl_input,
            am.name as id_ai,
            res.default_code as kode_customer,
            res.name as nama_customer,
            aj.name as payment_method,
            ac.code as code,
            ac.code || '-' ||ac.name as account,
            aml.name as description,
            case when right(aj.name,6) = 'LEDGER' and aml.debit > 0 then 0 
            else case when right(aj.name,6) = 'LEDGER' and aml.credit > 0 then aml.credit 
            else case when right(aj.name,17) = 'TITIPAN LAIN-LAIN' and aml.debit > 0 then 0 
            else case when right(aj.name,17) = 'TITIPAN LAIN-LAIN' and aml.credit > 0 then aml.credit
            else coalesce(aml.credit,0) end end end end as nilai_titipan,
            aac.code || '-'|| aac.name as account_analytic,
            av.number as journal_item,
            case when av.value_date <= '%s' then av.value_date else null end as tgl_alokasi,
            case when av.value_date <= '%s' then coalesce(avl.amount,0) 
            else case when right(aj.name,6) = 'LEDGER' and aml.debit > 0 then aml.debit
            else case when right(aj.name,6) = 'LEDGER' and aml.credit > 0 then 0
            else case when right(aj.name,17) = 'TITIPAN LAIN-LAIN' and aml.debit > 0 then aml.debit 
            else case when right(aj.name,17) = 'TITIPAN LAIN-LAIN' and aml.credit > 0 then 0
            else 0 end end end end end as nilai_alokasi,
            case when av.value_date <= '%s' then (case when aml.debit > 0 then aml.debit else case when aml.credit > 0 then aml.credit end end) - coalesce(avl.amount,0) 
            else case when right(aj.name,6) = 'LEDGER' and aml.debit > 0 then 0 - aml.debit
            else case when right(aj.name,6) = 'LEDGER' and aml.credit > 0 then aml.credit - 0
            else case when right(aj.name,17) = 'TITIPAN LAIN-LAIN' and aml.debit > 0 then 0 - aml.debit 
            else case when right(aj.name,17) = 'TITIPAN LAIN-LAIN' and aml.credit > 0 then aml.credit - 0
            else coalesce(aml.credit,0) - 0 end end end end end as sisa_titipan,
            '' as dpb_id,
            '' as dpbl_id,
            '' as am_id,
            0 as id,
            0 as drj_id,
            0 as sin_id
        from account_move am
        left join account_move_line aml on am.id = aml.move_id and right(am.name,9) != '(reclass)'
        left join dym_branch db on aml.branch_id = db.id
        left join res_partner res on am.partner_id = res.id
        left join account_account ac on aml.account_id = ac.id
        left join account_journal aj on am.journal_id = aj.id
        left join account_voucher_line avl on avl.move_line_id = aml.id and avl.type = 'dr'
        left join account_voucher av on avl.voucher_id = av.id
        left join account_analytic_account aac on avl.account_analytic_id = aac.id
        where left(am.name,3) in ('CDE','JRM','JDA','PAR') and (left(av.number,3) in ('CPA','SPA') or av.number is null)
        """ % (str(end_date),str(end_date),str(end_date))

        query_ttp_lain_reclass = """ union
            --OPBAL LAINLAIN
            SELECT   db.name as cabang,
            db.code as branch_id,
        aml.id,
            aml.division as divisi,
            am.date tgl_input,
            am.name as id_ai,
            res.default_code as kode_customer,
            res.name as nama_customer,
            aj.name as payment_method,
            ac.code as code,
            ac.code || '-' ||ac.name as account,
            aml.name as description,
            case when right(am.name,9) = '(reclass)' then 0 else coalesce(aml.credit,0) end as nilai_titipan,
            aac.code || '-'|| aac.name as account_analytic,
            av.number as journal_item,
            case when right(am.name,9) = '(reclass)' and av.value_date <= '%s' then av.value_date else null end as tgl_alokasi,
            case when right(am.name,9) = '(reclass)' and av.value_date <= '%s' then coalesce(avl.amount,0) else 0 end as nilai_alokasi,
            case when right(am.name,9) = '(reclass)' and av.value_date <= '%s' then 0 - aml.credit else aml.credit - coalesce(avl.amount,0) end as sisa_titipan,
            --av.value_date as tgl_alokasi,
            --case when right(am.name,9) = '(reclass)' then aml.credit else coalesce(avl.amount,0) end as nilai_alokasi,
            --case when right(am.name,9) = '(reclass)' then 0 - aml.credit else aml.credit - coalesce(avl.amount,0) end as sisa_titipan,
            '' as dpb_id,
            '' as dpbl_id,
            '' as am_id,
            0 as id,
            0 as drj_id,
            0 as sin_id
        from account_move am
        left join account_move_line aml on am.id = aml.move_id  
        left join dym_branch db on aml.branch_id = db.id
        left join res_partner res on am.partner_id = res.id
        left join account_account ac on aml.account_id = ac.id
        left join account_journal aj on am.journal_id = aj.id
        left join account_voucher_line avl on avl.move_line_id = aml.id and avl.type = 'dr'
        left join account_voucher av on avl.voucher_id = av.id
        left join account_analytic_account aac on avl.account_analytic_id = aac.id
        where   left(am.name,3) in ('CDE','JRM') and (left(av.number,3) in ('CPA','SPA') or av.number is null)
        and right(am.name,9) = '(reclass)' and aml.credit > 0
        """ % (str(end_date),str(end_date),str(end_date))

        move_selection = ""
        report_info = _('')
        move_selection += ""
    
        reports = [report_titipan_customer]

        if titipan in ('2105001 Titipan Uang Muka Konsumen'):
            query_order = " order by 5"
        elif titipan in ('2105002 Titipan STNK'):
            query_order = " order by 2,5,21"
        else:
            query_order = " order by 2,4,5"
        for report in reports:
            if titipan == '2105001 Titipan Uang Muka Konsumen':
                cr.execute(query_ttp_um_combined_rev)
                # print query_ttp_um_combined_rev + query_end_branch + query_end_date + query_end_ac_code + query_order
            elif titipan == '2105002 Titipan STNK' :
                cr.execute(query_ttp_stnk + query_end_branch + query_end_date + query_ttp_stnk_opbal + query_end_branch + query_order)
                # print query_ttp_stnk + query_end_branch + query_end_date + query_ttp_stnk_opbal + query_end_branch + query_order
            elif titipan == '2105099 Titipan Lain-lain' :
                cr.execute(query_ttp_lain + query_end_branch + query_end_ac_code + query_end_date + query_ttp_lain_reclass + query_end_branch + query_end_ac_code + query_order)
                #print query_ttp_lain + query_end_branch + query_end_ac_code + query_end_date + query_ttp_lain_reclass + query_end_branch + query_end_ac_code + query_order
            all_lines = cr.dictfetchall()
            
            move_lines = []
            if all_lines : 
                if titipan == '2105002 Titipan STNK':
                    p_map = map(lambda x:{
                        'branch_id': x['branch_id'].encode('ascii','ignore').decode('ascii') if x['branch_id'] != None else '',
                        'cabang': x['cabang'].encode('ascii','ignore').decode('ascii') if x['cabang'] != None else '',  
                        'divisi': x['divisi'].encode('ascii','ignore').decode('ascii') if x['divisi'] != None else '',                                       
                        'tgl_input': str(x['tgl_input']) if x['tgl_input'] != None else '',
                        'tgl_alokasi': str(x['tgl_alokasi']) if x['tgl_alokasi'] != None else '',
                        'id_ai': x['id_ai'].encode('ascii','ignore').decode('ascii') if x['id_ai'] != None else '',
                        'kode_customer': x['kode_customer'].encode('ascii','ignore').decode('ascii') if x['kode_customer'] != None else '',
                        'nama_customer': x['nama_customer'].encode('ascii','ignore').decode('ascii') if x['nama_customer'] != None else '',
                        'payment_method': x['payment_method'].encode('ascii','ignore').decode('ascii') if x['payment_method'] != None else '',    
                        'account': x['account'].encode('ascii','ignore').decode('ascii') if x['account'] != None else '',    
                        'description': x['description'].encode('ascii','ignore').decode('ascii') if x['description'] != None else '',    
                        'nilai_titipan': x['nilai_titipan'],
                        'account_analytic': x['account_analytic'].encode('ascii','ignore').decode('ascii') if x['account_analytic'] != None else '',    
                        'journal_item' : x['journal_item'].encode('ascii','ignore').decode('ascii') if x['journal_item'] != None else '',   
                        'nilai_alokasi': x['nilai_alokasi'],
                        'sisa_titipan': x['sisa_titipan'],
                        'total_tagihan': x['total_tagihan'],
                        'total_jasa': x['total_jasa'],
                        'selisih_margin': x['selisih_margin'],
                        'dpbl_id': x['dpbl_id'],
                        'dpb_id': x['dpb_id'],
                        'am_id': x['am_id'],
                        'id': x['id'],
                        'drj_id': x['drj_id'],
                        'sin_id': x['sin_id'],
                        'pajak_progresif' : x['pajak_progresif'],
                        'pajak_progresif_cde' : x['pajak_progresif_cde'],
                        'pajak_progresif_nde' : x['pajak_progresif_nde'],
                        },                       
                        all_lines)
                else:
                    p_map = map(lambda x:{
                        'branch_id': x['branch_id1'].encode('ascii','ignore').decode('ascii') if titipan == '2105001 Titipan Uang Muka Konsumen' else x['branch_id'].encode('ascii','ignore').decode('ascii'),
                        'cabang': x['cabang'].encode('ascii','ignore').decode('ascii') if x['cabang'] != None else '',  
                        'divisi': x['divisi'].encode('ascii','ignore').decode('ascii') if x['divisi'] != None else '',                                       
                        'tgl_input': str(x['tgl_input']) if x['tgl_input'] != None else '',
                        'tgl_alokasi': str(x['tgl_alokasi']) if x['tgl_alokasi'] != None else '',
                        'id_ai': x['id_ai'].encode('ascii','ignore').decode('ascii') if x['id_ai'] != None else '',
                        'kode_customer': x['kode_customer'].encode('ascii','ignore').decode('ascii') if x['kode_customer'] != None else '',
                        'nama_customer': x['nama_customer'].encode('ascii','ignore').decode('ascii') if x['nama_customer'] != None else '',
                        'payment_method': x['payment_method'].encode('ascii','ignore').decode('ascii') if x['payment_method'] != None else '',    
                        'account': x['account'].encode('ascii','ignore').decode('ascii') if x['account'] != None else '',    
                        'description': x['description'].encode('ascii','ignore').decode('ascii') if x['description'] != None else '',    
                        'nilai_titipan': x['nilai_titipan'],
                        'account_analytic': x['account_analytic'].encode('ascii','ignore').decode('ascii') if x['account_analytic'] != None else '',    
                        'journal_item' : x['journal_item'].encode('ascii','ignore').decode('ascii') if x['journal_item'] != None else '',   
                        'nilai_alokasi': x['nilai_alokasi'],
                        'sisa_titipan': x['sisa_titipan'],
                        'dpbl_id': x['dpbl_id'],
                        'dpb_id': x['dpb_id'],
                        'am_id': x['am_id'],
                        'id': x['id'],
                        'drj_id': x['drj_id'],
                        'sin_id': x['sin_id'],
                        },                       
                        all_lines)

                nomorsama = []
                ceknomor = ''
                res = []
                for p in p_map:
                    if titipan == '2105001 Titipan Uang Muka Konsumen':
                        if '(Reversed)' not in p['journal_item']:
                            if '(reclass)' not in p['id_ai']:
                                if ceknomor == p['id_ai']:
                                    nomorsama.append(p)
                                elif ceknomor != p['id_ai']:
                                    if nomorsama:
                                        sisa = nomorsama[0]['nilai_titipan']
                                        for y in nomorsama:
                                            y['nilai_titipan'] = sisa
                                            sisa = sisa - y['nilai_alokasi']
                                            y['sisa_titipan'] = sisa
                                            res.append(y)
                                        if sisa == 0:
                                            for z in res:
                                                z['sisa_titipan'] = 0
                                                move_lines.append(z)
                                        else:
                                            cektglalokasi = False
                                            for z in res:
                                                if not z['tgl_alokasi']:
                                                    cektglalokasi = True
                                            if cektglalokasi:
                                                for z in res:
                                                    if z['tgl_alokasi']:
                                                        z['sisa_titipan'] = 0
                                                    move_lines.append(z)
                                            else:
                                                for z in res:
                                                    move_lines.append(z)
                                        res = []
                                    ceknomor = p['id_ai']
                                    nomorsama = []
                                    nomorsama.append(p)
                            else:
                                move_lines.append(p)
                        else:
                            move_lines.append(p)
                    elif titipan == '2105002 Titipan STNK':
                        if (p['journal_item'] != '/' and p['id_ai'][:3] == 'DSM') or p['id_ai'][4:-11] == 'NUM':
                            proses_birojasa_state = self.pool.get('dym.proses.birojasa').browse(cr, uid, p['dpb_id'])
                            if proses_birojasa_state.state not in ('cancel','except_invoice'):
                                if ((p['id_ai'] not in map(lambda x: x.get('id_ai', None), move_lines)) and (p['dpb_id'] and p['dpbl_id'])) or ((p['id_ai'] not in map(lambda x: x.get('id_ai', None), move_lines)) and (not p['dpb_id'] and not p['dpbl_id'])):
                                    move_lines.append(p)
                                    if titipan == '2105002 Titipan STNK':
                                        proses_birojasa_lines = self.pool.get('dym.proses.birojasa.line').browse(cr, uid, p['dpbl_id'])
                                        proses_birojasa = self.pool.get('dym.proses.birojasa').browse(cr, uid, p['dpb_id'])
                                        account_invoice = self.pool.get('account.invoice').browse(cr, uid, p['sin_id'])
                                        if proses_birojasa.state not in ('done','approved'):
                                            p.update({'journal_item':''})
                                        nilai_alokasi = proses_birojasa_lines.titipan
                                        total_tagihan = proses_birojasa_lines.total_tagihan
                                        total_jasa = proses_birojasa_lines.total_jasa
                                        if p['id_ai'][:3] == 'DSM':
                                            dso_lines = self.pool.get('dealer.sale.order').browse(cr, uid, p['id'])
                                            tgl_alokasi = proses_birojasa.tanggal
                                            if p['am_id'] and not p['journal_item'] :
                                                nilai_titipan = p['nilai_titipan']
                                            else:
                                                nilai_titipan = dso_lines.amount_bbn
                                            if p['journal_item'][:3] == 'TBJ' and tgl_alokasi <= end_date and not p['drj_id']:
                                                selisih = nilai_titipan - nilai_alokasi
                                                selisih_margin = nilai_titipan - total_tagihan + total_jasa
                                                p.update({'tgl_alokasi':tgl_alokasi})
                                                p.update({'nilai_alokasi':nilai_alokasi})
                                                p.update({'total_tagihan':total_tagihan})
                                                p.update({'total_jasa':total_jasa})
                                                p.update({'selisih_margin':selisih_margin})
                                                p.update({'sisa_titipan':selisih})
                                            else:
                                                if p['drj_id']:
                                                    selisih = nilai_titipan - nilai_titipan
                                                    selisih_margin = nilai_titipan - total_tagihan + total_jasa
                                                    p.update({'tgl_alokasi':None})
                                                    p.update({'nilai_alokasi':nilai_titipan})
                                                    p.update({'total_tagihan':total_tagihan})
                                                    p.update({'total_jasa':total_jasa})
                                                    p.update({'selisih_margin':selisih_margin})
                                                    p.update({'sisa_titipan':selisih})
                                                else:
                                                    selisih = nilai_titipan - 0
                                                    p.update({'tgl_alokasi':None})
                                                    p.update({'nilai_alokasi':0})
                                                    p.update({'total_tagihan':0})
                                                    p.update({'total_jasa':0})
                                                    p.update({'selisih_margin':0})
                                                    p.update({'sisa_titipan':selisih})
                                        elif p['id_ai'][4:-11] == 'NUM':
                                            if user_branch_type == 'HO':
                                                am_lines = self.pool.get('account.move').browse(cr, SUPERUSER_ID, p['am_id'])
                                                aml_lines = self.pool.get('account.move.line').browse(cr, SUPERUSER_ID, p['id']) 
                                            else:
                                                am_lines = self.pool.get('account.move').browse(cr, uid, p['am_id'])
                                                aml_lines = self.pool.get('account.move.line').browse(cr, uid, p['id']) 
                                            nilai_titipan = aml_lines.credit
                                            move_ids = self.pool.get('account.move').search(cr, uid, [('ref','ilike',proses_birojasa.name)])
                                            if move_ids:
                                                if user_branch_type == 'HO':
                                                    move_date_ids = self.pool.get('account.move').browse(cr, SUPERUSER_ID, move_ids)
                                                else:
                                                    move_date_ids = self.pool.get('account.move').browse(cr, uid, move_ids)
                                                tgl_alokasi = move_date_ids[0].date
                                                if p['journal_item'][:3] == 'TBJ' and tgl_alokasi <= end_date:
                                                    selisih = nilai_titipan - nilai_alokasi
                                                    selisih_margin = nilai_titipan - total_tagihan + total_jasa
                                                    p.update({'tgl_alokasi':tgl_alokasi})
                                                    p.update({'nilai_alokasi':nilai_alokasi})
                                                    p.update({'total_tagihan':total_tagihan})
                                                    p.update({'total_jasa':total_jasa})
                                                    p.update({'selisih_margin':selisih_margin})
                                                    p.update({'sisa_titipan':selisih})
                                                elif p['journal_item'][:3] == 'TBJ' and tgl_alokasi > end_date:
                                                    selisih = nilai_titipan - 0
                                                    p.update({'tgl_alokasi':None})
                                                    p.update({'nilai_alokasi':0})
                                                    p.update({'total_tagihan':0})
                                                    p.update({'total_jasa':0})
                                                    p.update({'selisih_margin':0})
                                                    p.update({'sisa_titipan':selisih})
                                                else:
                                                    selisih = nilai_titipan - 0
                                                    p.update({'tgl_alokasi':None})
                                                    p.update({'nilai_alokasi':0})
                                                    p.update({'total_tagihan':0})
                                                    p.update({'total_jasa':0})
                                                    p.update({'selisih_margin':0})
                                                    p.update({'sisa_titipan':selisih})
                                            else:
                                                selisih = nilai_titipan - 0
                                                p.update({'tgl_alokasi':None})
                                                p.update({'nilai_alokasi':0})
                                                p.update({'total_tagihan':0})
                                                p.update({'total_jasa':0})
                                                p.update({'selisih_margin':0})
                                                p.update({'sisa_titipan':selisih})
                    else:
                        move_lines.append(p)
                report.update({'move_lines': move_lines})
        reports = filter(lambda x: x.get('move_lines'), reports)

        if not reports :
            reports = [{'title_short': 'Laporan Piutang Invoice', 'type': ['out_invoice','in_invoice','in_refund','out_refund'], 'move_lines':
                    [{
                        'no':0,                                      
                        'cabang': 'NO DATA FOUND',
                        'branch_id': 'NO DATA FOUND',
                        'divisi': 'NO DATA FOUND',
                        'tgl_input': 'NO DATA FOUND',
                        'tgl_alokasi': 'NO DATA FOUND',
                        'id_ai': 'NO DATA FOUND',
                        'kode_customer': 'NO DATA FOUND',
                        'nama_customer': 'NO DATA FOUND',
                        'payment_method': 'NO DATA FOUND',
                        'account': 'NO DATA FOUND',
                        'description': 'NO DATA FOUND',  
                        'nilai_titipan': 0.0,
                        'account_analytic': 'NO DATA FOUND',
                        'journal_item': 'NO DATA FOUND', 
                        'nilai_alokasi': 0.0,
                        'sisa_titipan':0.0,}], 'title': ''
                    }]

        report_date = datetime_field.context_timestamp(
            cr, uid, datetime.now(), context
            ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        self.localcontext.update({
            'report_info': report_info,
            'report_date': report_date,
            'reports': reports,
        })
        objects = False
        super( dym_titipan_customer_report_print, self).set_context(
            objects, data, ids, report_type)

    def formatLang_zero2blank(self, value, digits=None, date=False, date_time=False,
                   grouping=True, monetary=False, dp=False,
                   currency_obj=False):
        if isinstance(value, (float, int)) and not value:
            return ''
        else:
            return super(dym_report_hutan_invoice_print, self).formatLang(
                value, digits, date, date_time, grouping,
                monetary, dp, currency_obj)

class wrapped_vat_declaration_print(orm.AbstractModel):
    _name = 'report.dym_titipan_customer_report.report_titipan_customer'
    _inherit = 'report.abstract_report'
    _template = 'dym_titipan_customer_report.report_titipan_customer'
    _wrapped_report_class =  dym_titipan_customer_report_print
