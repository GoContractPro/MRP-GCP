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

from openerp import models, fields, api, exceptions, _
from jinja2 import defaults


class ProductionSalesMargin(models.Model):
    
    _name = 'production.sale.margin'
    
    name = fields.Char('Name', size = 32)
    multiplier = fields.Float('Multiplier')
    


class sale_order_line(models.Model):
    
    _inherit = ["sale.order.line"]
    
    '''@api.one
    @api.depends('analytic_line_ids','product_uom_qty', 'analytic_line_ids.estim_avg_cost',
                 )
    def get_unit_avg_cost(self):
        
        cost = 0.0
        for  line in self.analytic_line_ids:
            cost += line.estim_avg_cost
        self.avg_cost = cost
        self.unit_avg_cost = self.avg_cost / self.product_uom_qty
    '''
        
    @api.multi
    def _get_margin(self):
        
        return self.env.ref('mrp_sale_ficticious.25_percent_prod_sale_margin',False)
    

    
    production_id = fields.Many2one('mrp.production', 'MFG Quote')
    production_actual_id = fields.Many2one('mrp.production', 'MFG Production order')
#    production_avg_cost = fields.Float(string="Estimated Cost",
#                            compute="get_unit_avg_cost", store=True)
    production_avg_cost = fields.Float('MFG Unit Estimated Cost')
    production_sale_margin_id = fields.Many2one('production.sale.margin','Mfg Sales Multiplier ')
    analytic_line_ids = fields.One2many(comodel_name="account.analytic.line", inverse_name="sale_order_line_id",string="Cost Lines")
    is_approved = fields.Boolean('Production Approved')
    
    
    _defaults = {
            'production_sale_margin_id': _get_margin                                       
            }
        

    @api.multi
    @api.onchange('production_sale_margin_id')
    def onchange_production_sale_margin(self, production_sale_margin_id=None):
        res = {}
        margin = self.env['production.sale.margin'].browse(production_sale_margin_id)
        
        
        if production_sale_margin_id:
            res['value']= {'price_unit': self.production_avg_cost * margin.multiplier }

        return res
      
    @api.multi
    def action_view_mos(self):
        
        if self.production_id:
        
            result = {
                    "type": "ir.actions.act_window",
                    "res_model": "mrp.production",
                    "views": [[False, "form"]],
                    "res_id": self.production_id.id,
                    "target": "window",
                    }
        
            return result
        else:
            
            return False

    @api.multi
    def button_cancel(self):
        res = super(sale_order_line,self).button_cancel()
        return res
    
    
    @api.multi
    def button_confirm(self):
        
        line_delete = []
        line_confirm = []
        line_name_delete = []
        sale_line_obj = self.env['sale.order.line']
        for sale_line in self:
            if sale_line.production_id and not sale_line.is_approved :
                line_delete.append(sale_line.id)
                line_name_delete.append("Line:" + str(sale_line.sequence) + "-" + sale_line.name)
            else:
                line_confirm.append(sale_line.id)
        if line_delete:
#           self.show_warning('\n'.join(line_name_delete) + "\n" + _("Will Be Removed"))
            sale_line_obj.browse(line_delete).unlink()
        
#        sale_lines = self.env['sale.order.line'].browse(ids)
        sale_line_obj = sale_line_obj.browse(line_confirm)
        res = super(sale_order_line,sale_line_obj).button_confirm()
            
        return  res
    
    
    @api.multi
    def get_production_sale_line_price(self):
        
        if self.production_id:
            self.production_id.create_sale_analytic_production_estimated_cost(sale_order_line=self)
        else:
            raise exceptions.Warning(
                    _("Sales line has no MFG orders."))
     
        analytic_line_obj = self.env['account.analytic.line']
        analytic_lines = analytic_line_obj.search([('sale_order_line_id','=',self.id)])
        production_cost = sum([line.estim_avg_cost for line in
                             analytic_lines])
        
        unit_avg_cost =  - production_cost / self.product_uom_qty
        
        if self.production_sale_margin_id :
            
            price = unit_avg_cost * (self.production_sale_margin_id.multiplier or 1.0)
        
        else:
            price = 1.0

        vals = {'production_avg_cost':unit_avg_cost,
                'purchase_price': unit_avg_cost,
                'price_unit':price,
                }
        
        return vals
    
    @api.multi
    def update_mfg_sale_line_price(self):
        
        if self.production_id:
            prices = self.get_production_sale_line_price()
            self.write(prices)
        return True
                
    @api.multi
    def action_approve(self):
        
        
        if not self.is_approved:
            vals = {'is_approved':True}
            res = {'value':vals}
        else:    
            vals = {'is_approved':False}
            res = {'value':vals}
        self.write(vals)
        return res
    
    

    
    @api.multi
    def action_show_estimated_costs(self):
        self.ensure_one()
        analytic_line_obj = self.env['account.analytic.line']
        id2 = self.env.ref(
            'mrp_production_project_estimated_cost.estimated_cost_list_view')
        search_view = self.env.ref('mrp_project_link.account_analytic_line'
                                   '_mrp_search_view')
        analytic_line_list = analytic_line_obj.search(
            [('sale_order_line_id', '=', self.id),
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
    
    @api.multi
    @api.onchange('product_uom')  
    def product_uom_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False):
        
        return super(sale_order_line,self).product_id_change(pricelist, product,
                qty=qty, uom=uom, qty_uos=qty_uos, uos=uos, name=name,
                partner_id=partner_id, lang=lang, update_tax=update_tax,
                date_order=date_order)
        
    @api.multi 
    @api.onchange('product_id','product_uom_qty')
    def product_id_change_sale_mfg(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False,
            fiscal_position=False, flag=False, warehouse_id=False, production_id=False):
        
        res = self.product_id_change_with_wh( pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag, warehouse_id=warehouse_id)
        
        if self.production_id:
            
            prices = self.get_production_sale_line_price()
            res['value']['purchase_price'] = prices.get('purchase_price',0.0)
            res['value']['production_avg_cost'] = prices.get('production_avg_cost',0.0)
            res['value']['price_unit'] = prices.get('price_unit',0.0)
         
        if not res['value'].get('product_id',False): res['value']['product_id'] = product
        
       
        if not res['value'].get('product_uom_qty', False): res['value']['product_uom_qty'] = qty
        if not res['value'].get('product_uom',False): res['value']['product_uom'] = uom
        if not res['value'].get('product_uos_qty',False): res['value']['product_uos_qty'] = qty
        if not res['value'].get('product_uos',False): res['value']['product_uos'] = uos
        if not res['value'].get('name',False): res['value']['name'] = name
        if not res['value'].get('product_packaging',False): res['value']['product_packaging'] = packaging
        if not res['value'].get('production_id',False): res['value']['production_id'] = production_id
        if not res['value'].get('production_sale_margin_id'): res['value']['production_sale_margin_id'] = self.production_sale_margin_id.id
        if not res['value'].get('state',False): res['value']['state'] = 'draft'
        
        return res
        
        return super(sale_order_line,self).copy(defaults)

class sale_order(models.Model):
    _inherit = "sale.order"
   
    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur = order.pricelist_id.currency_id
            
            for line in order.order_line:
                val1 += line.price_subtotal
                val += self._amount_line_tax(cr, uid, line, context=context)
            res[order.id]['amount_tax'] = cur_obj.round(cr, uid, cur, val)
            res[order.id]['amount_untaxed'] = cur_obj.round(cr, uid, cur, val1)
            res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res
     
    @api.multi
    def create_mfg_quote(self):
         
        return {'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wiz.sale.create.fictitious',
                'type': 'ir.actions.act_window',
                'target':'new',
                }
 

    @api.multi
    def copy(self,default = None):
        
        if not default: 
            default = {}
        
        
        default['main_project_id'] = False
        default['project_id'] = False
        
        
        res = super(sale_order,self).copy(default)
        
        for line in res.order_line:
                
            if line.production_actual_id:
                    
                line.write({'production_actual_id':False})
            
        
        return res
        