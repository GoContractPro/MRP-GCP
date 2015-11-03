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
from openerp.addons.product import _common

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


    def ceiling(self,f,r):
        if not r:
            return f
        return math.ceil(f/r)*r
        
    def _bom_extract_prod(self, cr, uid, bom, factor, addthis=False, context={}):
                 
        def _factor(factor, product_efficiency, product_rounding):
            factor = factor / (product_efficiency or 1.0)
            factor = _common.ceiling(factor, product_rounding)
            if factor < product_rounding:
                factor = product_rounding
            return factor

        factor = _factor(factor, bom.product_efficiency, bom.product_rounding)       
        result = []        
        for bom_line_id in bom.bom_line_ids:
            if bom_line_id.date_start and bom_line_id.date_start > time.strftime(DEFAULT_SERVER_DATE_FORMAT) or \
                bom_line_id.date_stop and bom_line_id.date_stop < time.strftime(DEFAULT_SERVER_DATE_FORMAT):
                    continue
            # all bom_line_id variant values must be in the product
            product = bom.product_id
            if bom_line_id.attribute_value_ids:
                if not product or (set(map(int,bom_line_id.attribute_value_ids or [])) - set(map(int,product.attribute_value_ids))):
                    continue
 
            quantity = _factor(bom_line_id.product_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding)
            bom_id = self.pool.get('mrp.bom')._bom_find(cr, uid, product_id=bom_line_id.product_id.id, properties=[], context=context)
 
            #If BoM should not behave like PhantoM, just add the product, otherwise explode further
            if bom_line_id.type != "phantom" and (not bom_id or self.pool.get('mrp.bom').browse(cr, uid, bom_id, context=context).type != "phantom"):
#                 if addthis:
                result.append({
                    'name': bom_line_id.product_id.name,
                    'product_id': bom_line_id.product_id.id,
                    'product_qty': quantity,
                    'product_uom': bom_line_id.product_uom.id,
                    'product_uos_qty': bom_line_id.product_uos and _factor(bom_line_id.product_uos_qty * factor, bom_line_id.product_efficiency, bom_line_id.product_rounding) or False,
                    'product_uos': bom_line_id.product_uos and bom_line_id.product_uos.id or False,
                    #Verts Added sequence field
                    'bom_seq' : bom_line_id.sequence,
                })
                if bom_id:
                    bom1 = self.pool.get('mrp.bom').browse(cr, uid, bom_id, context=context)
                    res = self._bom_extract_prod(cr, uid, bom1, factor,addthis=True)
                    result = result + res
            elif bom_id:
                bom2 = self.pool.get('mrp.bom').browse(cr, uid, bom_id, context=context)
                # We need to convert to units/UoM of chosen BoM
                factor2 = uom_obj._compute_qty(cr, uid, bom_line_id.product_uom.id, quantity, bom2.product_uom.id)
                quantity2 = factor2 / bom2.product_qty
                res = self._bom_extract_prod(cr, uid, bom2, factor,addthis=True)
                result = result + res
            else:
                raise osv.except_osv(_('Invalid Action!'), _('BoM "%s" contains a phantom BoM line but the product "%s" does not have any BoM defined.') % (master_bom.name,bom_line_id.product_id.name_get()[0][1]))
 
        return result
                
    def _prepare_lines(self, cr, uid, production, properties=None, context=None):
        # search BoM structure and route
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        bom_point = production.bom_id
        bom_id = production.bom_id.id
        if not bom_point:
            bom_id = bom_obj._bom_find(cr, uid, product_id=production.product_id.id, properties=properties, context=context)
            if bom_id:
                bom_point = bom_obj.browse(cr, uid, bom_id)
                routing_id = bom_point.routing_id.id or False
                self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

        if not bom_id:
            raise osv.except_osv(_('Error!'), _("Cannot find a bill of material for this product."))

        # get components and workcenter_lines from BoM structure
        factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, production.product_qty, bom_point.product_uom.id)
        # product_lines, workcenter_lines
        return self._bom_extract_prod(cr, uid, bom_point, factor / bom_point.product_qty)
    
    def _search_suitable_rule(self, cr, uid, location, product, domain, context=None):
        '''we try to first find a rule among the ones defined on the procurement order group and if none is found, we try on the routes defined for the product, and finally we fallback on the default behavior'''
        pull_obj = self.pool.get('procurement.rule')
#         warehouse_route_ids = []
#         if procurement.warehouse_id:
#             domain += ['|', ('warehouse_id', '=', procurement.warehouse_id.id), ('warehouse_id', '=', False)]
#             warehouse_route_ids = [x.id for x in procurement.warehouse_id.route_ids]
        product_route_ids = [x.id for x in product.route_ids + product.categ_id.total_route_ids]
        res = pull_obj.search(cr, uid, domain + [('route_id', 'in', product_route_ids)], order='route_sequence, sequence', context=context)
        if not res:
            res = pull_obj.search(cr, uid, domain + [('route_id', '=', False)], order='sequence', context=context)
        return res
    
    def _find_parent_locations(self, cr, uid, location, context=None):
        res = [location.id]
        while location.location_id:
            location = location.location_id
            res.append(location.id)
        return res
   
    def _find_suitable_rule(self, cr, uid, location, product, context=None):
        all_parent_location_ids = self._find_parent_locations(cr, uid, location, context=context)
        rule_id = self._search_suitable_rule(cr, uid, location, product, [('location_id', 'in', all_parent_location_ids)], context=context)
        rule_id = rule_id and rule_id[0] or False
        if rule_id:
            rule_id = self.pool.get('procurement.rule').browse(cr,uid,rule_id)
        return rule_id
    
    @api.multi
    def do_create_fictitious_of_sale(self):
        production_obj = self.env['mrp.production']
        project_model = self.env['project.project']
        sale_line_obj = self.env['sale.order.line']
        product_obj = self.env['product.product']
        self.ensure_one()
        active_id = self.env.context['active_id']
        active_model = self.env.context['active_model']
        
        if not self.product_qtys:
            raise exceptions.Warning(_("Please Specify A Product Quantity"))
            return
        
        if active_model == 'sale.order':      
            
            if not self.project_id and not self.sale_order_id.main_project_id:
                
                project_obj = project_model.create({'name':self.sale_order_id.name})
                self.project_id = project_obj.id
                self.sale_order_id.write({"project_id":project_obj.analytic_account_id.id,
                                      "main_project_id":project_obj.id})
            elif self.project_id and not self.sale_order_id.main_project_id:
                
                self.sale_order_id.write({"project_id":project_obj.analytic_account_id.id,
                                      "main_project_id":project_obj.id})
                
            elif self.project_id != self.sale_order_id.main_project_id:
                raise exceptions.Warning(_("You have set Project different than the Sales Order Project"))
        
            sequence_obj = self.env['ir.sequence']
            name = sequence_obj.get('sale.mrp.production')
            project_obj = project_model.create({'name':name})
            
            
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
                        'name':name,
                        'project_id': project_obj.id,
                        'analytic_account_id':project_obj.analytic_account_id.id
                        }
                
                sale_production = production_obj.create(vals)
                
            else:
                sale_production = self.production_id
            
            sale_production.action_compute()
            sale_production.calculate_production_estimated_cost()

#===============================================================================
# #                 Create Sub assemblies production orders : 
#===============================================================================
            bom_extract_data = self._prepare_lines(sale_production)
            for res in bom_extract_data:
                product = product_obj.browse(res['product_id'])
                if product.type not in ('product', 'consu'):
                    continue
                procure_method = production_obj._get_raw_material_procure_method(product, location_id=sale_production.location_src_id.id, location_dest_id=product.property_stock_production.id, context={})
                
                rule_id = self._find_suitable_rule(sale_production.location_src_id, product, context={})
                if procure_method == 'make_to_order' and rule_id and rule_id.action == 'manufacture':
                    sub_name = sequence_obj.get('sale.mrp.production')
                    sub_project_obj = project_model.create({'name':sub_name})
                    sub_project_obj.analytic_account_id.parent_id = self.project_id.analytic_account_id.id
                    sub_vals = {'product_id': res['product_id'],
                        'product_qty': res['product_qty'],
                        'date_planned': self.date_planned,
                        'user_id': self._uid,
                        'active': True,
                        'is_sale_quote':True,
                        'product_uom' :self.product_uom.id,
                        'production_id' :sale_production.id,
#                         'bom_id': self.bom_id.id,
#                         'routing_id' : self.routing_id.id,                  
                        'sale_order_id': active_id,
                        'name':name + '-' + sub_name,
                        'project_id': sub_project_obj.id,
                        'analytic_account_id':sub_project_obj.analytic_account_id.id
                        }
                
                    sub_production = production_obj.create(sub_vals)
                    sub_production.action_compute()
                    sub_production.calculate_production_estimated_cost()
            for qty in self.product_qtys:              
                sale_line = sale_line_obj.create({'order_id':active_id,
                                              'product_id':self.product_id.id,
                                              'name': (self.name or ''),
                                              'production_sale_margin_id':self.production_sale_margin_id.id,
                                              'product_uom_qty':qty.product_qty,
                                              'production_id':sale_production.id,
                                              'mfg_quote':True,
                                              'mrp_routing_id':self.routing_id and self.routing_id.id or False
                                              })
                
#               prices = sale_line.get_sale_line_production_price_vals(product_uom_qty = qty.product_qty, production_sale_margin_id = self.production_sale_margin_id.id)
                
                
                result = sale_line.product_id_change_sale_mfg(sale_line.order_id.pricelist_id.id, sale_line.product_id.id,sale_line.product_uom_qty,
                                            uom=sale_line.product_uom.id, qty_uos =  sale_line.product_uos_qty, uos=sale_line.product_uos.id, 
                                            name=sale_line.name, partner_id=sale_line.order_id.partner_id.id, lang=False, update_tax=True, 
                                            date_order=sale_line.order_id.date_order, packaging=False, fiscal_position=sale_line.order_id.fiscal_position.id, 
                                            flag=False,production_id=sale_line.production_id.id)
                
                '''
                vals = result['value']
                
               
                vals['price_unit']= prices.get('price_unit',0.0)
                vals['production_avg_cost'] = prices.get('production_avg_cost',0.0)
                vals['purchase_price'] = prices.get('purchase_price',0.0)            
                '''
                sale_line.write(result['value'])
                
                
#             sale_production.action_compute()
#             sale_production.calculate_production_estimated_cost()
            
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
    
    

    