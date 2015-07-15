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

class procurement_rule(models.Model):
    _inherit = 'procurement.rule'

    @api.multi
    def _get_action(self):
        return [('sale_manufacture', _('Sales MFG Quoted'))] + super(procurement_rule, self)._get_action()


class MrpProduction(models.Model):
    _inherit = 'mrp.production'
    
    
    sale_order_line_id = fields.Many2one("sale.order.line", string= "Sales Line", ondelete='cascade')
    sale_order_id = fields.Many2one("sale.order", string= "Sales Line")
    sale_project_id =  fields.Many2one("project.project", string="Sales Project")
    is_sale_quote = fields.Boolean("Confirmed Quote")
              
    
    
    @api.multi
    def calculate_production_estimated_cost(self):
        
        super(MrpProduction, self).calculate_production_estimated_cost()
        
        unit_std_cost = -self.unit_std_cost
        unit_avg_cost = -self.unit_avg_cost
        
        if self.sale_order_line_id.production_sale_margin_id :
            
            price = unit_avg_cost * (self.sale_order_line_id.production_sale_margin_id.multiplier or 1.0)
        
        else:
            price = 1.0

        self.sale_order_line_id.write({'production_avg_cost':unit_avg_cost,
                                'purchase_price': unit_avg_cost,
                                'production_std_cost': unit_std_cost,
                                'price_unit':price,
                                'product_uom_qty':self.product_qty })
    
    @api.multi
    def action_show_estimated_costs(self):
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        id2 = self.env.ref(
            'mrp_production_project_estimated_cost.estimated_cost_list_view')
        search_view = self.env.ref('mrp_project_link.account_analytic_line'
                                   '_mrp_search_view')
        analytic_line_list = analytic_line_obj.search(
            [('mrp_production_id', '=', self.id),
             ('task_id', '=', False)])
        self = self.with_context(
                                 search_default_group_workorder=1,
                                 search_default_group_journal=1)
        return {
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.analytic.line',
            'views': [(id2.id, 'tree')],
            'search_view_id': search_view.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'window',
            'domain': "[('id','in',[" +
            ','.join(map(str, analytic_line_list.ids)) + "])]",
            'context': self.env.context
            }



    @api.model
    def create(self, values):
        sequence_obj = self.env['ir.sequence']
        if values.get('is_sale_quote', True):
            values['name'] = sequence_obj.get('sale.mrp.production')
        else:
            if values.get('active', True):
                values['active'] = True
                if values.get('name', '/') == '/':
                    values['name'] = sequence_obj.get('mrp.production')
            else:
                values['name'] = sequence_obj.get('fictitious.mrp.production')
        
            
        return super(MrpProduction, self).create(values)
    
    @api.one
    def write(self, vals):
        
        if 'product_qty' in vals and not vals.get('product_qty'):
        
            self.calculate_production_estimated_cost()
            self.env.cr.commit()
            
        return super(MrpProduction, self).write(vals)

        