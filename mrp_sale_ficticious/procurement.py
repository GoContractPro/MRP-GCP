# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 novapointgroup inc.
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

from openerp import models, fields, api, exceptions, _
from unittest2 import result

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    
    def make_mo(self, cr, uid, ids, context=None):
        """ Make Manufacturing(production) order from procurement or from copy of Sales Line MFG Quote
        @return: New created Production Orders procurement wise
        """
        procurement_obj = self.pool.get('procurement.order')
        for procurement in procurement_obj.browse(cr, uid, ids, context=context):
            if procurement.sale_line_id and procurement.sale_line_id.production_id:
                return self.copy_sales_mo(cr, uid, procurement, context=context)
            
        return super(procurement_order, self).make_mo(cr, uid, ids, context=context)
    
   
    def copy_sales_mo(self, cr, uid, procurement, context=None):
 
        res ={}
        production_obj = self.pool.get('mrp.production')   
        defaults = self._prepare_mo_vals(cr, uid, procurement, context=context)
        defaults['sale_order_line_id'] = procurement.sale_line_id.id         
        defaults['sale_order_id'] = procurement.sale_line_id.order_id.id
        defaults['analytic_account_id'] = procurement.main_project_id.analytic_account_id.id
        defaults['project_id'] = procurement.main_project_id.id       
        defaults['is_sale_quote'] = False
        defaults['origin'] = (procurement.sale_line_id.order_id.name or '') + "[MFG-" + (procurement.name or '') + "]"

        new_production = procurement.sale_line_id.production_id.copy(defaults)

        qty =  procurement.product_qty
        
        for work_line in new_production.workcenter_lines:
            cycle = work_line.cycle * qty
            hour = work_line.hour * qty
            vals = {'cycle':cycle,
                   'hour':hour
                   }
           
            work_line.write(vals)
            
        for product_line in new_production.product_lines:
            product_qty = product_line.product_qty * qty
            vals = {
                    'product_qty':product_qty}
            product_line.write(vals)
    
        procurement.sale_line_id.write({'production_actual_id':new_production.id})
#            self.write(cr, uid, [procurement.id], {'production_id': new_production.id})
        self.production_order_create_note(cr, uid, procurement, context=context)
        production_obj.signal_workflow(cr, uid, [new_production.id], 'button_confirm')

        res[procurement.id] = new_production
            
        return res
    

    def _prepare_mo_vals(self, cr, uid, procurement, context=None):
    

        res =  super(procurement_order, self)._prepare_mo_vals(cr, uid, procurement, context=context)
        
        if procurement and procurement.main_project_id and procurement.main_project_id.analytic_account_id:
            
            res['analytic_account_id'] = procurement.main_project_id.analytic_account_id.id
            res['project_id'] = procurement.main_project_id.id

        return res  


            
        
    