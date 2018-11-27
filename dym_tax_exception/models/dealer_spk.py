# -*- coding: utf-8 -*-

import pdb
import itertools
import openerp.addons.decimal_precision as dp

from lxml import etree
from datetime import datetime, timedelta
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.addons.dym_base import DIVISION_SELECTION
from openerp.osv import osv


class DealerSPK(models.Model):
    _inherit = "dealer.spk"

    @api.multi
    def action_create_so(self):
        branch_config_id = self.env['dym.branch.config'].search([('branch_id','=',self.branch_id.id)])

        sale_order_line=[]
        payment_term = False
        if self.finco_id and self.partner_id:
            payment_term = self.finco_id.property_payment_term.id
        else:
            payment_term = self.partner_id.property_payment_term.id
        if self.is_pic:
            pajak_satuan=True
            pajak_gunggung=False
            pajak_gabungan=False
        else:
            # pajak_satuan=False
            if self.partner_id.npwp and not self.partner_id.tipe_faktur_pajak:
                raise Warning("Tipe Faktur Pajak di master Customer belum dilengkapi")
            elif not self.partner_id.npwp and self.partner_id.tipe_faktur_pajak != 'tanpa_fp':
                raise Warning("Nomor NPWP atau Tipe Faktur Pajak di master Customer belum dilengkapi")
            # elif self.partner_id.npwp and self.partner_id.tipe_faktur_pajak == 'tanpa_fp':
            #     raise Warning("Tipe Faktur Pajak tidak boleh diisi 'Tanpa Faktur Pajak' di master Customer jika ada NPWP")
            elif not self.partner_id.npwp and not self.partner_id.tipe_faktur_pajak:
                raise Warning("Tipe Faktur Pajak di master Customer belum dilengkapi")
                
            if self.partner_id.tipe_faktur_pajak == 'tanpa_fp':
                pajak_gunggung=True
                pajak_satuan=False
                pajak_gabungan=False
            elif self.partner_id.tipe_faktur_pajak == 'satuan':
                pajak_gunggung=False
                pajak_satuan=True
                pajak_gabungan=False
            elif self.partner_id.tipe_faktur_pajak == 'gabungan':
                pajak_gunggung=False
                pajak_satuan=False
                pajak_gabungan=True

        sale_order = {
            'branch_id': self.branch_id.id,
            'division': self.division,
            'date_order': datetime.now().strftime('%Y-%m-%d'),
            'partner_id': self.partner_id.id,
            'partner_cabang':self.partner_cabang.id, 
            'employee_id': self.employee_id.id,
            'sales_source': self.sales_source.id,
            'finco_id': self.finco_id.id if self.is_credit else False,     
            'dealer_spk_id': self.id,
            'register_spk_id': self.register_spk_id.id,
            'is_pic': self.is_pic,
            'cddb_id': False,
            'section_id':self.section_id.id,      
            'is_credit':self.is_credit, 
            'finco_cabang':self.finco_cabang.id, 
            'alamat_kirim':self.alamat_kirim,
            'payment_term': payment_term,                 
            'origin': self.origin,
            'pricelist_id': self.pricelist_id.id,
            'proposal_id': self.proposal_id.id,
            'pajak_generate': pajak_satuan,
            'pajak_gunggung': pajak_gunggung,
            'pajak_gabungan': pajak_gabungan,
        }
        so_line_cddb_ids = []
        for line in self.dealer_spk_line:
            for number in range(line.product_qty):
                plat = False
                stnk = False
                tanda_jadi = 0.0
                uang_muka = False
                biro_jasa_branch = False
                price_bbn = 0.0
                total = 0.0
                price_bbn_beli = 0.0
                price_bbn_notice = 0.0
                price_bbn_proses = 0.0
                price_bbn_jasa = 0.0
                price_bbn_jasa_area = 0.0
                price_bbn_fee_pusat = 0.0
                city = False
                if line.uang_muka:
                    uang_muka = line.uang_muka

                if self.pricelist_id.id:
                    price = self._get_price_unit(self.pricelist_id.id, line.product_id.id)
                elif self.branch_id.pricelist_unit_sales_id.id:
                    price = self._get_price_unit(self.branch_id.pricelist_unit_sales_id.id, line.product_id.id)
                else:
                    raise Warning('Pricelist jual unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                
                if price <= 0:
                    raise Warning('Pricelist unit %s 0 rupiah, silahkan di set di pricelist cabang terlebih dahulu' %(line.product_id.name))
                
                if line.is_bbn == 'Y':
                    if line.partner_stnk_id.sama == True:
                        city =  line.partner_stnk_id.city_id.id
                    else:
                        city =  line.partner_stnk_id.city_tab_id.id
                    if not city:
                        raise Warning('Alamat customer STNK Belum lengkap!')
                    if self.branch_id.pricelist_bbn_hitam_id.id:
                        price_bbn = self._get_price_unit(self.branch_id.pricelist_bbn_hitam_id.id, line.product_id.id)
                    else:
                        raise Warning('Pricelist jual BBN unit Cabang "%s" belum ada, silahkan buat dulu' %(self.branch_id.name))
                    if price_bbn <= 0:
                        raise Warning('Pricelist bbn unit %s 0 rupiah, silahkan di set di pricelist cabang terlebih dahulu' %(line.product_id.name))
                    
                location_lot = self._get_location_id_branch(line.product_id.id,self.branch_id.id)
                
                if location_lot:
                    lot_id = location_lot[0].lot_id.id
                    location_id = location_lot[0].location_id.id
                    price_unit_beli = location_lot[0].lot_id.hpp
                    location_lot[0].lot_id.write({'state':'reserved'})
                else:
                    raise Warning('Tidak ditemukan stock produk')


                tax_id = [(6,0,[x.id for x in line.product_id.taxes_id])]
                if branch_config_id.free_tax:
                	tax_id = False
                
                values = {
                    'categ_id': 'Unit',
                    'template_id': line.template_id.id,
                    'product_id': line.product_id.id,
                    'product_qty': 1,
                    'is_bbn': line.is_bbn,
                    'plat': plat,
                    'partner_stnk_id': line.partner_stnk_id.id,
                    'location_id': location_id,
                    'lot_id': lot_id,
                    'price_unit': price,
                    'biro_jasa_id': biro_jasa_branch or False,  
                    'price_bbn': price_bbn or 0.0,
                    'price_bbn_beli': price_bbn_beli or 0.0,
                    'tanda_jadi': line.tanda_jadi or 0.0,
                    'tanda_jadi2': self.is_credit and line.tanda_jadi or 0.0,
                    'uang_muka': uang_muka or 0.0,
                    'price_unit_beli':price_unit_beli or 0.0,
                    'price_bbn_notice': price_bbn_notice or 0.0,
                    'price_bbn_proses': price_bbn_proses or 0.0,
                    'price_bbn_jasa': price_bbn_jasa or 0.0,
                    'price_bbn_jasa_area': price_bbn_jasa_area or 0.0,
                    'price_bbn_fee_pusat': price_bbn_fee_pusat or 0.0,
                    'tax_id': tax_id,
                    'city_id': city,
                    'discount_po': line.discount_po,
                    'diskon_dp': self.is_credit and line.discount_po or 0.0,
                }
                if line.cddb_id:
                    so_line_cddb_ids.append((4,[line.cddb_id.id]))
                sale_order_line.append([0,False,values])
        sale_order['dealer_sale_order_line'] = sale_order_line
        if so_line_cddb_ids:
            sale_order['cddb_id'] = so_line_cddb_ids

        create_so = self.env['dealer.sale.order'].create(sale_order)
        self.register_spk_id.write({'state':'so','dealer_sale_order_id':create_so.id})
        self.write({
            'state':'so',
            'dealer_sale_order_id':create_so.id,
            'user_create_so_id': self._uid,
            'so_create_date':datetime.now().strftime('%Y-%m-%d'),
        })        
        return create_so