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

from openerp import models, fields, api, _


class ProductionSalesMargin(models.Model):
    
    _name = 'production.sale.margin'
    
    name = fields.Char('Name', size = 32)
    multiplier = fields.Float('Multiplier')
    


class sale_order_line(models.Model):
    
    _inherit = ["sale.order.line"]
    
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',ondelete='cascade')
    production_avg_cost = fields.Float('MFG Unit Average Cost')
    production_std_cost = fields.Float('MFG Unit Standard Cost')
    production_sale_margin_id = fields.Many2one('production.sale.margin','Mfg Sales Multiplier ')
    
    @api.multi
    def _get_margin(self):
        
        return self.env.ref('mrp_sale_ficticious.25_percent_prod_sale_margin',False)
    
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
        res = super(sale_order_line,self).button_confirm()
#        sale_lines = self.env['sale.order.line'].browse(ids)
        
        for sale_line in self:
            if sale_line.production_id:
                sequence_obj = self.env['ir.sequence']
                if sale_line.production_id.is_sale_quote:
                    name = sequence_obj.get('mrp.production')
                    sale_line.production_id.write({'is_sale_quote':False,'name':name,})
        return  res 

    
class sale_order(models.Model):
    _inherit = "sale.order"
    
    @api.multi
    def create_mfg_quote(self):
        
        
        return {'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wiz.sale.create.fictitious',
                'type': 'ir.actions.act_window',
                'target':'new',
                }
 

