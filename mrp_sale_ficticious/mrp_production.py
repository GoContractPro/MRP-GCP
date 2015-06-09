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

from openerp import models, fields, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    
    sale_order_line_id = fields.Many2one("sale.order.line", string= "Sales Line")
    sale_order_id = fields.Many2one("sale.order", string= "Sales Line")
    sale_project_id =  fields.Many2one("project.project", string="Sales Project")
              
    
    
    @api.multi
    def calculate_production_estimated_cost(self):
        
        super(MrpProduction, self).calculate_production_estimated_cost()
        
        std_cost = self.unit_std_cost
        avg_cost = self.unit_avg_cost
        
        if self.sale_order_line_id.production_sale_margin_id :
            
            price = avg_cost * (self.sale_order_line_id.production_sale_margin_id.multiplier or 1.0)
        
        else:
            price = 1.0

        self.sale_order_line_id.write({'production_avg_cost':avg_cost,
                                  'production_std_cost':std_cost,
                                  'price_unit':price,
                                  'product_uom_qty':self.product_qty })



        