    def action_invoice_create(self, cr, uid, ids, context=None):
        sale_order = self.browse(cr, uid, ids, context)
        if not sale_order or not sale_order.ensure_one():
            raise osv.except_osv(_('Error!'),
                _('action_invoice_create() method only for single object.'))
        elif not sale_order.dealer_sale_order_line:
            raise osv.except_osv(_('Error!'),
                _('Harap isi detil sale order terlebih dahulu.'))

        obj_inv = self.pool.get('account.invoice') 
        account_id = False
        ar_branch_id = False
        ap_branch_id = False
        default_supplier = False
        invoice_customer = {}
        invoice_customer_line = []
        invoice_finco = {}
        invoice_finco_line = []
        invoice_pelunasan = {}
        invoice_pelunasan_line = []
        invoice_bbn = {}
        invoice_bbn_line = []
        invoice_insentif_finco = {}
        invoice_insentif_finco_line = []
        invoice_hc = {}
        invoice_hc_line = []
        analytic_1, analytic_2, analytic_3, analytic_4 = self.pool.get('account.analytic.account').get_analytical(cr, uid, sale_order.branch_id, 'Unit', False, 4, 'Sales')
        analytic_1_general, analytic_2_general, analytic_3_general, analytic_4_general = self.pool.get('account.analytic.account').get_analytical(cr, uid, sale_order.branch_id, 'Unit', False, 4, 'General')
        obj_bbn = self.pool.get('dym.harga.bbn.line')

        obj_branch_config = self._get_branch_journal_config(cr,uid,sale_order.branch_id.id)
        finco = False
        if not obj_branch_config.dealer_so_journal_pic_id.default_debit_account_id.id and not obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id and not sale_order.partner_id.property_account_receivable.id:
            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet jurnal pelunasan penjualan regular atau intercompany dan account receivable di customer belum lengkap!"))
        
        qq2_ids = []
        for l in sale_order.dealer_sale_order_line:
            if l.partner_stnk_id:
                qq2_ids.append(l.partner_stnk_id.id)
        if qq2_ids:
            qq2_ids = [(6,0,qq2_ids)]

        if sale_order.is_pic:
            journal_id = obj_branch_config.dealer_so_journal_pic_id.id
            account_id = obj_branch_config.dealer_so_journal_pic_id.default_debit_account_id.id or sale_order.partner_id.property_account_receivable.id,
        else:
            journal_id = obj_branch_config.dealer_so_journal_pelunasan_id.id
            account_id = obj_branch_config.dealer_so_journal_pelunasan_id.default_debit_account_id.id or sale_order.partner_id.property_account_receivable.id,

        if sale_order.finco_id:
            finco = sale_order.finco_id.id
            invoice_pelunasan = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'finco',
                'qq_id': sale_order.partner_id.id,
                'qq2_id': qq2_ids,
                'journal_id': journal_id,
                'account_id': account_id,
                'payment_term': sale_order.payment_term.id,
                'section_id':sale_order.section_id.id,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
            }
            invoice_insentif_finco = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.finco_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'insentif',
                'qq_id': sale_order.partner_id.id,
                'qq2_id': qq2_ids,
                'journal_id': obj_branch_config.dealer_so_journal_insentive_finco_id.id,
                'account_id': obj_branch_config.dealer_so_journal_insentive_finco_id.default_debit_account_id.id,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
            }
        else:
             invoice_pelunasan = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'out_invoice', 
                'tipe': 'customer',
                'journal_id': journal_id,
                'account_id': account_id,
                'payment_term': sale_order.payment_term.id,
                'section_id':sale_order.section_id.id,   
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,               
            }
        
        if sale_order.partner_komisi_id:
            if not (obj_branch_config.dealer_so_journal_hc_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_hc_id.default_debit_account_id.id):
                raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal HC belum lengkap!"))
            invoice_hc = {
                'name':sale_order.name,
                'origin': sale_order.name,
                'branch_id':sale_order.branch_id.id,
                'division':sale_order.division,
                'partner_id':sale_order.partner_komisi_id.id,
                'date_invoice':sale_order.date_order,
                'reference_type':'none',
                'type': 'in_invoice', 
                'tipe': 'hc',
                'journal_id': obj_branch_config.dealer_so_journal_hc_id.id,
                'account_id': obj_branch_config.dealer_so_journal_hc_id.default_credit_account_id.id,
                'analytic_1': analytic_1_general,
                'analytic_2': analytic_2_general,
                'analytic_3': analytic_3_general,
                'analytic_4': analytic_4_general,
            }

        per_product = {}
        per_potongan = {}
        per_barang_bonus = {}
        per_invoice = []
        per_ar = []
        for line in sale_order.dealer_sale_order_line:
            
            if not per_product.get(line.product_id.id,False):
                per_product[line.product_id.id] = {}
                
            per_product[line.product_id.id]['product_qty'] = per_product[line.product_id.id].get('product_qty',0)+line.product_qty
            per_product[line.product_id.id]['price_unit'] = per_product[line.product_id.id].get('price_unit',0)+line.price_unit
            per_product[line.product_id.id]['force_cogs'] = per_product[line.product_id.id].get('force_cogs',0)+line.force_cogs
            per_product[line.product_id.id]['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
            
            if line.is_bbn == 'Y':
                per_product[line.product_id.id]['price_bbn'] = per_product[line.product_id.id].get('price_bbn',0)+line.price_bbn
                per_product[line.product_id.id]['product_qty_bbn'] = per_product[line.product_id.id].get('product_qty_bbn',0)+line.product_qty
            if line.hutang_komisi_id and line.amount_hutang_komisi:
                per_product[line.product_id.id]['amount_hutang_komisi'] = per_product[line.product_id.id].get('amount_hutang_komisi',0)+line.amount_hutang_komisi
            
            per_product[line.product_id.id]['customer_dp'] = per_product[line.product_id.id].get('customer_dp',0)+line.uang_muka
            insentif_finco = line._get_insentif_finco_value(finco,sale_order.branch_id.id)
            self.write(cr, uid, line.id, {'insentif_finco':insentif_finco})
            per_product[line.product_id.id]['insentif_finco'] = per_product[line.product_id.id].get('insentif_finco',0)+insentif_finco
            per_potongan['discount_po'] = per_potongan.get('discount_po',0)+line.discount_po
            per_potongan['tax_id'] = [(6, 0, [y.id for y in line.tax_id])]
            
            date_due_default = datetime.now().strftime('%Y-%m-%d')
            date_due_finco = datetime.now().strftime('%Y-%m-%d')
            if sale_order.finco_id.property_payment_term:
                pterm_list = sale_order.finco_id.property_payment_term.compute(value=1, date_ref=date_due_finco)[0]
                if pterm_list:
                    date_due_finco = max(line[0] for line in pterm_list)
            if sale_order.branch_id.default_supplier_id.property_payment_term:
                pterm_list = sale_order.branch_id.default_supplier_id.property_payment_term.compute(value=1, date_ref=date_due_default)[0]
                if pterm_list:
                    date_due_default = max(line[0] for line in pterm_list)

            for disc in line.discount_line:
                invoice_ps_finco = {}
                invoice_ps_finco_line = []
                
                if disc.include_invoice == False:
                    continue

                if disc.tipe_diskon == 'percentage':
                    total_diskon = disc.discount_pelanggan
                    if disc.tipe_diskon == 'percentage':
                        total_diskon = line.price_unit * disc.discount_pelanggan / 100
                    per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon*line.product_qty)
                else:
                    total_claim_discount = disc.ps_ahm + disc.ps_md + disc.ps_finco + disc.ps_others + disc.ps_dealer
                    total_diskon_pelanggan = 0 if total_claim_discount - disc.discount_pelanggan >= disc.ps_dealer else disc.ps_dealer - (total_claim_discount - disc.discount_pelanggan)
                    total_diskon_external = disc.discount_pelanggan - total_diskon_pelanggan
                    per_potongan['discount_external'] = per_potongan.get('discount_external',0)+(total_diskon_external*line.product_qty)
                    per_potongan['discount_pelanggan'] = per_potongan.get('discount_pelanggan',0)+(total_diskon_pelanggan*line.product_qty)
                if disc.tipe_diskon == 'percentage':
                    continue
                discount_gap = 0.0
                discount_md = 0.0
                discount_finco = 0.0
                discount_oi = 0.0
                sisa_ke_finco = False
                
                if disc.discount_pelanggan != disc.discount:
                     discount_gap =  disc.discount - disc.discount_pelanggan
                taxes = [(6, 0, [y.id for y in line.tax_id])]
                
                if disc.ps_finco > 0:
                    if not (obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_psfinco_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS Finco belum lengkap!"))
                    if not sale_order.finco_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Financial company perlu didefinisikan untuk program subsidi " + disc.program_subsidi.name + "!"))
                    invoice_ps_finco = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.finco_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_finco, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_psfinco_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    
                    if discount_gap >0:
                        if disc.ps_finco > discount_gap: 
                            discount_finco = disc.ps_finco - discount_gap
                            discount_oi = discount_gap
                            sisa_ke_finco = True
                        elif disc.ps_finco == discount_gap:
                            discount_finco = disc.ps_finco
                        else:
                            discount_oi = discount_gap - disc.ps_finco
                            discount_finco = disc.ps_finco - discount_oi
                            discount_gap = discount_gap - discount_oi
                        
                        if discount_finco > 0:   
                            invoice_ps_finco_line.append([0,False,{
                                'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount': discount_finco,
                                'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id':analytic_4,  
                            }])
                        
                        if discount_oi>0:
                            invoice_ps_finco_line.append([0,False,{
                                'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount':discount_oi,
                                'account_id': obj_branch_config.dealer_so_account_sisa_subsidi_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id':analytic_4,  
                            }])
                        
                    else:
                        invoice_ps_finco_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'amount':disc.ps_finco,
                            'account_id': obj_branch_config.dealer_so_journal_psfinco_id.default_credit_account_id.id,
                            'type': 'cr',
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                        sisa_ke_finco = True
                        
                    invoice_ps_finco['line_cr_ids'] = invoice_ps_finco_line
                    per_ar.append(invoice_ps_finco)
                
                if (disc.ps_ahm > 0 or disc.ps_md > 0):
                    invoice_md = {}
                    invoice_md_line = []
        
                    if not (obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_psmd_id.default_debit_account_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal PS MD belum lengkap!"))
                    if not sale_order.branch_id.default_supplier_id.id:
                        raise osv.except_osv(('Perhatian !'), ("Principle di branch belum diisi, silahkan setting dulu!"))
                    invoice_md = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.branch_id.default_supplier_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_default, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_psmd_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    
                    if sisa_ke_finco == False:
                        if discount_gap >0:
                            if (disc.ps_md+disc.ps_ahm) >= discount_gap:
                                discount_md = disc.ps_md+disc.ps_ahm-discount_gap
                                discount_oi = discount_gap
                            else:
                                discount_md = discount_gap - disc.ps_md- disc.ps_ahm
                            
                            if discount_md>0:  
                                invoice_md_line.append([0,False,{
                                    'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                    'amount': discount_md,
                                    'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id,
                                    'type': 'cr',
                                    'analytic_1': analytic_1,
                                    'analytic_2': analytic_2,
                                    'analytic_3': analytic_3,
                                    'account_analytic_id':analytic_4,  
                                }])
                            
                            if discount_oi>0:
                                invoice_md_line.append([0,False,{
                                    'name': 'Sisa subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                    'amount': discount_gap,
                                    'account_id': obj_branch_config.dealer_so_account_sisa_subsidi_id.id,
                                    'type': 'cr',
                                    'analytic_1': analytic_1,
                                    'analytic_2': analytic_2,
                                    'analytic_3': analytic_3,
                                    'account_analytic_id':analytic_4,  
                                }])
                        else:
                            invoice_md_line.append([0,False,{
                                'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                                'amount': disc.ps_ahm+disc.ps_md,
                                'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id,
                                'type': 'cr',
                                'analytic_1': analytic_1,
                                'analytic_2': analytic_2,
                                'analytic_3': analytic_3,
                                'account_analytic_id':analytic_4,  
                            }])
                        
                    else:
                        invoice_md_line.append([0,False,{
                            'name': 'Subsidi '+disc.program_subsidi.name+' '+line.product_id.name,
                            'amount': disc.ps_ahm+disc.ps_md,
                            'account_id': obj_branch_config.dealer_so_journal_psmd_id.default_credit_account_id.id,
                            'type': 'cr',
                            'analytic_1': analytic_1,
                            'analytic_2': analytic_2,
                            'analytic_3': analytic_3,
                            'account_analytic_id':analytic_4,  
                        }])
                            
                    invoice_md['line_cr_ids'] = invoice_md_line
                    
                    per_ar.append(invoice_md)

            for barang_bonus in line.barang_bonus_line:
                if not per_barang_bonus.get(barang_bonus.product_subsidi_id.id,False):
                    per_barang_bonus[barang_bonus.product_subsidi_id.id] = {}
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['product_qty'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('product_qty',0)+ barang_bonus.barang_qty
                per_barang_bonus[barang_bonus.product_subsidi_id.id]['force_cogs'] = per_barang_bonus[barang_bonus.product_subsidi_id.id].get('force_cogs',0)+barang_bonus.price_barang
                if barang_bonus.bb_md > 0 or barang_bonus.bb_ahm > 0:
                    invoice_bb_md = {}
                    invoice_bb_md_line = []
                    
                    if not (obj_branch_config.dealer_so_journal_bbmd_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbmd_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi belum lengkap!"))
                    invoice_bb_md = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.branch_id.default_supplier_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_default, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_bbmd_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_bbmd_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    invoice_bb_md_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'amount': barang_bonus.bb_ahm+barang_bonus.bb_md,
                        'account_id': obj_branch_config.dealer_so_journal_bbmd_id.default_credit_account_id.id,
                        'type': 'cr',
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }]]
                    invoice_bb_md['line_cr_ids'] = invoice_bb_md_line
                    per_ar.append(invoice_bb_md)
                if barang_bonus.bb_finco > 0:
                    invoice_bb_finco = {}
                    invoice_bb_finco_line = []
                    if not (obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id and obj_branch_config.dealer_so_journal_bbfinco_id.id):
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account debet kredit jurnal Barang Subsidi Finco belum lengkap!"))
                    invoice_bb_finco = {
                        'branch_id':sale_order.branch_id.id,
                        'division':sale_order.division,
                        'partner_id':sale_order.finco_id.id,
                        'date':datetime.now().strftime('%Y-%m-%d'), 
                        'date_due': date_due_finco, 
                        'reference': sale_order.name, #
                        'name':sale_order.name,
                        'user_id': sale_order.user_id.id,
                        'journal_id': obj_branch_config.dealer_so_journal_bbfinco_id.id,
                        'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_debit_account_id.id,
                        'type': 'sale',
                        'analytic_1': analytic_1_general,
                        'analytic_2': analytic_2_general,
                        'analytic_3': analytic_3_general,
                        'analytic_4': analytic_4_general,
                    }
                    invoice_bb_finco_line = [[0,False,{
                        'name': 'Subsidi '+barang_bonus.barang_subsidi_id.name+' '+line.product_id.name,
                        'amount': barang_bonus.bb_finco,
                        'account_id': obj_branch_config.dealer_so_journal_bbfinco_id.default_credit_account_id.id,
                        'type': 'cr',
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }]]
                    invoice_bb_finco['line_cr_ids'] = invoice_bb_finco_line
                    per_ar.append(invoice_bb_finco)

        if sale_order.customer_dp > 0:
            invoice_pelunasan['amount_dp'] = sale_order.customer_dp
            invoice_pelunasan['account_dp'] = obj_branch_config.dealer_so_account_dp.id
        
        invoice_pelunasan['tanda_jadi'] = sale_order.tanda_jadi
            
        if sale_order.amount_bbn > 0:
            invoice_pelunasan['amount_bbn'] = sale_order.amount_bbn
            invoice_pelunasan['account_bbn'] = obj_branch_config.dealer_so_account_bbn_jual_id.id

        for key, value in per_product.items():            
            product_id = self.pool.get('product.product').browse(cr,uid,key)
            product_income_account_id = self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id)
            if not product_income_account_id:
                raise osv.except_osv(_('Error!'),
                    _('Income account untuk produk %s belum diisi!') % \
                    (product_id.name))
            sale_account_id = self.pool.get('product.product')._get_account_id(cr,uid,ids,product_id.id)
            if sale_order.is_pic:
                sale_account_id = sale_account_id

            invoice_pelunasan_line.append([0,False,{
                'name': 'HMK' + product_id.name,
                'product_id':product_id.id,
                'quantity':value['product_qty'],
                'origin':sale_order.name,
                'price_unit':((value['price_unit'])/value['product_qty']),
                'invoice_line_tax_id': value['tax_id'],
                'account_id': sale_account_id.id,
                'force_cogs': value.get('force_cogs',0),
                'analytic_1': analytic_1,
                'analytic_2': analytic_2,
                'analytic_3': analytic_3,
                'account_analytic_id':analytic_4,  
            }])
            if value.get('insentif_finco',0) > 0:
                invoice_insentif_finco_line.append([0,False,{
                    'name': 'Insentif '+str(product_id.name),
                    'quantity': value['product_qty'],
                    'origin': sale_order.name,
                    'price_unit':value['insentif_finco']/value['product_qty'],
                    'invoice_line_tax_id': [(6,0,[2])],
                    'account_id': obj_branch_config.dealer_so_journal_insentive_finco_id.default_credit_account_id.id,
                    'analytic_1': analytic_1,
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'account_analytic_id':analytic_4,  
                }])
                
            if value.get('amount_hutang_komisi') > 0:
                invoice_hc_line.append([0,False,{
                    'name': 'Hutang Komisi '+str(product_id.name),
                    'quantity': value['product_qty'],
                    'origin': sale_order.name,
                    'price_unit':value['amount_hutang_komisi']/value['product_qty'],
                    'account_id': obj_branch_config.dealer_so_journal_hc_id.default_debit_account_id.id,
                    'analytic_1': analytic_1,
                    'analytic_2': analytic_2,
                    'analytic_3': analytic_3,
                    'account_analytic_id':analytic_4,  
                }])
        for key, value in per_potongan.items():
            if value > 0:
                price_unit = -1*value
                tax = per_potongan['tax_id']
                if key=='discount_po':
                    if not obj_branch_config.dealer_so_account_potongan_langsung_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan langsung di branch config belum ada!"))                    
                    account_discount_id = obj_branch_config.dealer_so_account_potongan_langsung_id
                    if sale_order.is_pic:
                        account_discount_id = obj_branch_config.dealer_so_account_potongan_pic_id
                        if not account_discount_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan inter company di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                        'name': 'Diskon Reguler',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':price_unit,
                        'invoice_line_tax_id':tax,
                        'account_id': account_discount_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }])
                
                if key=='discount_pelanggan':
                    # invoice_pelunasan['discount_program'] = value
                    if not obj_branch_config.dealer_so_account_potongan_subsidi_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi di branch config belum ada!"))                    
                    account_discount_id = obj_branch_config.dealer_so_account_potongan_subsidi_id
                    if sale_order.is_pic:
                        account_discount_id = obj_branch_config.dealer_so_account_potongan_pic_id
                        if not account_discount_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan inter company di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                        'name': 'Diskon Dealer',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':price_unit,
                        'invoice_line_tax_id':tax,
                        'account_id': account_discount_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }])
                if key=='discount_external':
                    # invoice_pelunasan['discount_program'] = value
                    if not obj_branch_config.dealer_so_account_potongan_subsidi_external_id:
                        raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan subsidi external di branch config belum ada!"))
                    account_discount_id = obj_branch_config.dealer_so_account_potongan_subsidi_external_id
                    if sale_order.is_pic:
                        account_discount_id = obj_branch_config.dealer_so_account_potongan_pic_id
                        if not account_discount_id:
                            raise osv.except_osv(('Perhatian !'), ("Konfigurasi account diskon potongan inter company di branch config belum ada!"))
                    invoice_pelunasan_line.append([0,False,{
                        'name': 'Diskon External',
                        'quantity':1,
                        'origin':sale_order.name,
                        'price_unit':price_unit,
                        'invoice_line_tax_id':tax,
                        'account_id': account_discount_id.id,
                        'analytic_1': analytic_1,
                        'analytic_2': analytic_2,
                        'analytic_3': analytic_3,
                        'account_analytic_id':analytic_4,  
                    }])
        if invoice_hc_line:
            invoice_hc['invoice_line']=invoice_hc_line
            create_invoice_hc = obj_inv.create(cr,uid,invoice_hc)
            obj_inv.button_reset_taxes(cr,uid,create_invoice_hc)
            workflow.trg_validate(uid, 'account.invoice', create_invoice_hc, 'invoice_open', cr)
            
        for value in per_invoice:
            create_invoice = obj_inv.create(cr,uid,value)
            obj_inv.button_reset_taxes(cr,uid,create_invoice)
            workflow.trg_validate(uid, 'account.invoice', create_invoice, 'invoice_open', cr)

        for value in per_ar:
            create_ar = self.pool.get('account.voucher').create(cr,uid,value,context=context)

        invoice_pelunasan['invoice_line']= invoice_pelunasan_line
        create_invoice_pelunasan = obj_inv.create(cr,uid,invoice_pelunasan)
        obj_inv.button_reset_taxes(cr,uid,create_invoice_pelunasan)
        workflow.trg_validate(uid, 'account.invoice', create_invoice_pelunasan, 'invoice_open', cr)
        if sale_order.amount_tax and not sale_order.pajak_gabungan and not sale_order.pajak_gunggung :   
            self.pool.get('dym.faktur.pajak.out').get_no_faktur_pajak(cr,uid,ids,'dealer.sale.order',context=context) 
        if sale_order.amount_tax and sale_order.pajak_gunggung == True :   
            self.pool.get('dym.faktur.pajak.out').create_pajak_gunggung(cr,uid,ids,'dealer.sale.order',context=context)
        return create_invoice_pelunasan 
