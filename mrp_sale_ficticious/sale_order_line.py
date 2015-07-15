# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _


class sale_order_line(osv.osv):
    
    _inherit = ["sale.order.line"]
    
    def product_id_change(self,cr,uid,ids,pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False,context=None):
        res = {}
        result = {}
        product_obj = self.pool.get('product.product')
        production_obj = self.pool.get('mrp.production')
        sale_line_obj = self.pool.get('sale.order.line').browse(cr,uid,ids)
        for sale_line in sale_line_obj:
        
            production_id = sale_line.production_id.id
            if production_id:
                product_obj = product_obj.browse(cr,uid,product)
                production_obj = production_obj.browse(cr,uid,production_id)
                production_obj.write({'product_qty':qty})
                production_obj.calculate_production_estimated_cost()
                result['purchase_price'] = -production_obj.unit_avg_cost
                price = -production_obj.unit_avg_cost * (sale_line.production_sale_margin_id.multiplier or 1.0)
                result['price_unit'] = price
                
                domain = {'product_uom':
                [('category_id', '=', product_obj.uom_id.category_id.id)],
                'product_uos':
                [('category_id', '=', product_obj.uos_id.category_id.id)]}
                
                res = {'value': result,'domian':domain}
            else:
                res = super(sale_order_line,self).product_id_change(pricelist, product, qty=qty,
                uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
                lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag,context=context)
            
        return res
    
    