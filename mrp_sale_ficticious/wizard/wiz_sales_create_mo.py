# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 NovaPoint Group INC (<http://www.novapointgroup.com>)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################


from openerp import models, fields, api, exceptions , _
import openerp.addons.decimal_precision as dp

class WizSaleCreateFictious(models.Model):
    _name = "wiz.sale.create.fictitious"

    name = fields.Text('Description', )
    date_planned = fields.Datetime(
        string='Scheduled Date', required=True, default=fields.Datetime.now())
    load_on_product = fields.Boolean("Load cost on product")
    project_id = fields.Many2one("project.project", string="Project")
    production_sale_margin_id = fields.Many2one('production.sale.margin','Mfg Sales Multiplier ')
    sale_order_id = fields.Many2one("sale.order", string= "Sales Order")
    product_id = fields.Many2one("product.product" , string="Product")
    production_id = fields.Many2one('mrp.production', 'MFG Quote', domain="[('is_sale_quote','=',True),('product_id','=',product_id)]")
    product_qtys = fields.One2many('wiz.sale.create.so.line.qty', 'mfg_sale_wiz_id', string='Quantities' )
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure',  readonly=False)
    product_uos_qty = fields.Float('Product UoS Quantity', readonly=False)
    product_uos = fields.Many2one('product.uom', 'Product UoS', readonly=False)
    bom_id = fields.Many2one('mrp.bom', 'Bill of Material', readonly=False,
            help="Bill of Materials allow you to define the list of required raw materials to make a finished product.")
    routing_id = fields.Many2one('mrp.routing', string='Routing', on_delete='set null', readonly=False,
            help="The list of operations (list of work centers) to produce the finished product. The routing is mainly used to compute work center costs during operations and to plan future loads on work centers based on production plannification.")


    @api.multi
    def do_create_fictitious_of_sale(self):
        production_obj = self.env['mrp.production']
        project_obj = self.env['project.project']
        sale_line_obj = self.env['sale.order.line']
        
        self.ensure_one()
        active_id = self.env.context['active_id']
        active_model = self.env.context['active_model']
        
        if not self.product_qtys:
            raise exceptions.Warning(_("Please Specify A Product Quantity"))
            return
        

        
        if active_model == 'sale.order':      
            
            if not self.project_id and not self.sale_order_id.main_project_id:
                
                project_obj = project_obj.create({'name':self.sale_order_id.name})
                self.project_id = project_obj.id
                self.sale_order_id.write({"project_id":project_obj.analytic_account_id.id,
                                      "main_project_id":project_obj.id})
            elif self.project_id and not self.sale_order_id.main_project_id:
                
                self.sale_order_id.write({"project_id":project_obj.analytic_account_id.id,
                                      "main_project_id":project_obj.id})
                
            elif self.project_id != self.sale_order_id.main_project_id:
                raise exceptions.Warning(_("You have set Project different than the Sales Order Project"))
        
            
            if not self.production_id:
                vals = {'product_id': self.product_id.id,
                        'product_qty': 1,
                        'date_planned': self.date_planned,
                        'user_id': self._uid,
                        'active': True,
                        'is_sale_quote':True,
                        'product_uom' :self.product_uom.id,
                        'bom_id': self.bom_id.id,
                        'routing_id' : self.routing_id.id,                  
                        'sale_order_id': active_id,
                        }
                
                sale_production = production_obj.create(vals)
            else:
                sale_production = self.production_id
            
            sale_production.action_compute()
            sale_production.calculate_production_estimated_cost()
            
#            if new_production.project_id and self.project_id.id:
#                new_production.project_id.write({"parent_id":self.project_id.id})
                
            for qty in self.product_qtys:              
                
                sale_line = sale_line_obj.create({'order_id':active_id,
                                              'product_id':self.product_id.id,
                                              'name': (self.name or ''),
                                              'production_sale_margin_id':self.production_sale_margin_id.id,
                                              'product_uom_qty':qty.product_qty,
                                              'production_id':sale_production.id,
                                              'mfg_quote':True,
                                              })
                
                prices = sale_line.get_production_sale_line_price(product_uom_qty = qty.product_qty, production_sale_margin_id = self.production_sale_margin_id.id)
                
                result = sale_line.product_id_change_sale_mfg(sale_line.order_id.pricelist_id.id, sale_line.product_id.id,sale_line.product_uom_qty,
                                            uom=sale_line.product_uom.id, qty_uos =  sale_line.product_uos_qty, uos=sale_line.product_uos.id, 
                                            name=sale_line.name, partner_id=sale_line.order_id.partner_id.id, lang=False, update_tax=True, 
                                            date_order=sale_line.order_id.date_order, packaging=False, fiscal_position=sale_line.order_id.fiscal_position.id, 
                                            flag=False,production_id=sale_line.production_id.id)
                vals = result['value']
                
                vals['price_unit']= prices.get('price_unit',0.0)
                vals['production_avg_cost'] = prices.get('production_avg_cost',0.0)
                vals['purchase_price'] = prices.get('purchase_price',0.0)            
                
                sale_line.write(vals)
            
        return{}
        
    def product_id_change(self, cr, uid, ids, product_id, context=None):
        """ Finds UoM of changed product.
        @param product_id: Id of changed product.
        @return: Dictionary of values.
        """
        result = {}
        if not product_id:
            return {'value': {
                'product_uom': False,
                'bom_id': False,
                'routing_id': False,
                'product_uos_qty': 0,
                'product_uos': False
            }}
        bom_obj = self.pool.get('mrp.bom')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        bom_id = bom_obj._bom_find(cr, uid, product_id=product.id, properties=[], context=context)
        routing_id = False
        if bom_id:
            bom_point = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom_point.routing_id.id or False
        product_uom_id = product.uom_id and product.uom_id.id or False
     
        name = 'Mfg--' + (product.name or product.description_sale)
            
        result['value'] = {'product_uos_qty': 0, 'product_uos': False, 
                        'product_uom': product_uom_id, 'bom_id': bom_id,
                        'routing_id': routing_id, 'name': name}
                
        if product.uos_id.id:
#            result['value']['product_uos_qty'] = product_qty * product.uos_coeff
            result['value']['product_uos'] = product.uos_id.id
            self.write(cr, uid, ids,result['value'],context=context)
            
            

                
        return result
    

    
    def default_get(self, cr, uid, fields, context=None):
        
        res = super(WizSaleCreateFictious, self).default_get(cr, uid, fields, context)    
        if context is None:
            context = {}  
        
              
        sale_order_obj = self.pool.get('sale.order').browse(cr, uid, context['active_id'], context=context)
              
        project =  sale_order_obj.main_project_id.id
        res['project_id'] = project
        res['sale_order_id'] = context['active_id']
        
        return res
    
class WizSaleCreateSOLineQty(models.Model):
        
    _name = 'wiz.sale.create.so.line.qty'
        
    product_qty = fields.Float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'))
    mfg_sale_wiz_id = fields.Many2one('wiz.sale.create.fictitious', string = 'Sale MFG Wizard')
    
    

    