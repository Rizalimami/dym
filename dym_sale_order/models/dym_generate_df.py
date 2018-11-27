import time
import base64
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
import pytz 

class Eksport_file_permata(osv.osv_memory):
    _name = "eksport.permata"
    _columns = {
                'name': fields.char('File Name', 35),
                'data_file': fields.binary('File'),
                'date_start':fields.date(string="Start Date",required=True),
                'date_end':fields.date(string="End Date",required=True)
                }   
    
    def export_file(self, cr, uid, ids, context=None):
        val = self.browse(cr, uid, ids)[0]
        trx_id = context.get('active_id',False) 
        trx_obj = self.pool.get('account.invoice').browse(cr,uid,trx_id,context=context)
        result = self.eksport_distribution(cr, uid, ids, trx_obj,context)
        form_id  = 'view.wizard.eksport.permata'
 
        view_id = self.pool.get('ir.ui.view').search(cr,uid,[                                     
                                                             ("name", "=", form_id), 
                                                             ("model", "=", 'eksport.permata'),
                                                             ])
     
        return {
            'name' : _('Export File'),
            'view_type': 'form',
            'view_id' : view_id,
            'view_mode': 'form',
            'res_id': ids[0],
            'res_model': 'eksport.permata',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context
        }
        
    def eksport_distribution(self, cr, uid, ids,trx_obj, context=None):
        result = '' 
        val = self.browse(cr, uid, ids)[0]
        cr.execute('''
                 select '40  ' || 
                right(replace(inv.number, '/', ''),7) as prefix, 
                --sequence 3 digit--
                to_char(date_order + interval '7 hours', 'MMDDYYYY') || 
                '                     ' || 
                right(replace(inv.number, '/', ''),7) ||
                to_char((date_order + interval '7 hours') + COALESCE(term_line.days,0) * interval '1 day', 'MMDDYYYY') || 
                '            ' || 
                to_char((date_order + interval '7 hours') + interval '45 days', 'MMDDYYYY') ||
                left(partner.default_code || '          ',10) || 
                left(partner.name || '                              ',30) || 
                left(product.default_code || '               ', 15) || 
                '                    ' || 
                left(pack_line.chassis_number || '                 ',17) ||
                left(pack_line.engine_number || '             ',13) || 
                left(COALESCE(pav.name,'') || '               ',15) ||
                left(sol.price_unit - (COALESCE(so.discount_cash,0) + COALESCE(so.discount_program,0) + COALESCE(so.discount_lain,0)) * 1.1 / solg.total_qty || '          ',10) as suffix
                from sale_order so
                inner join stock_picking pick on so.name = pick.origin and pick.state = 'done'
                inner join dym_stock_packing pack on pick.id = pack.picking_id
                inner join dym_stock_packing_line pack_line on pack.id = pack_line.packing_id and pack_line.engine_number is not null
                inner join stock_production_lot lot on lot.id = pack_line.serial_number_id
                inner join product_product product on product.id = pack_line.product_id
                left join sale_order_line sol on sol.order_id = so.id and sol.product_id = pack_line.product_id
                left join product_attribute_value_product_product_rel pavpp on product.id = pavpp.prod_id
                left join product_attribute_value pav on pavpp.att_id = pav.id
                left join dym_branch b on so.branch_id = b.id
                left join res_partner partner on so.partner_id = partner.id
                left join account_payment_term term on so.payment_term = term.id
                left join account_payment_term_line term_line on term.id = term_line.payment_id
                left join account_invoice inv on inv.origin = so.name
                left join (select order_id, sum(product_uom_qty) as total_qty from sale_order_line group by order_id) solg on solg.order_id = so.id
                where b.code = 'MML' and so.division = 'Unit' and so.state in ('progress','done')
                and pick.date_done >=%s and pick.date_done <=%s
                order by so.date_order,so.id
              ''',(val.date_start,val.date_end))
        picks = cr.fetchall()
        i=1
        prev_prefix=False
        for x in picks:
            if prev_prefix ==x[0] :
                i+=1
            else:
                i=1
            prev_prefix=x[0]
            
            if len(str(i)) == 1 :
                        urutan="00"+str(i)
            elif len(str(i)) == 2 :
                urutan="0"+str(i)
            elif len(str(i)) == 3 :
                urutan=str(i)
            result += x[0]+str(urutan)+x[1]
            result += '\n'
        tangal=time.strftime('%d%m%Y')
        nama = tangal+'.txt'
        out = base64.encodestring(result)
        distribution = self.write(cr, uid, ids, {'data_file':out, 'name': nama}, context=context)


       