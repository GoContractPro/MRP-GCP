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
    

    
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',ondelete='cascade')
#    production_avg_cost = fields.Float(string="Estimated Cost",
#                            compute="get_unit_avg_cost", store=True)
    production_avg_cost = fields.Float('MFG Unit Standard Cost')
    production_sale_margin_id = fields.Many2one('production.sale.margin','Mfg Sales Multiplier ')
    analytic_line_ids = fields.One2many(
    comodel_name="account.analytic.line", inverse_name="sale_line_id",
    string="Cost Lines")
    is_approved = fields.Boolean('Is Approved')
    
    
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
    @api.onchange('product_uom_qty')
    def onchange_product_uom_qty(self):
        
        if self.production_id:
            res = self.update_sales_line_prices()
        else:
            '''res = super(sale_order_line,self).product_id_change( pricelist, product, qty,
            uom, qty_uos, uos, name, partner_id,
            lang, update_tax, date_order, packaging, fiscal_position, flag)
            '''
            pass
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
    
    @api.model
    def calculate_production_estimated_cost(self):
        analytic_line_obj = self.env['account.analytic.line']
 #       for sale_line in self:
        cond = [('sale_line_id', '=', self.id)]
        analytic_line_obj.search(cond).unlink()
        journal = self.env.ref('mrp_production_project_estimated_cost.'
                                 'analytic_journal_materials', False)
        if not self.production_id:
            raise exceptions.Warning(
                    _("Sales line has no Production Order."))
            return
        else:
            production = self.production_id
        
        for line in production.product_lines:
            if not line.product_id:
                raise exceptions.Warning(
                    _("One consume line has no product assigned."))
            name = _('%s-%s' % (production.name, line.work_order.name or ''))
            product = line.product_id
            qty = line.product_qty * self.product_uom_qty
            vals = self._prepare_cost_analytic_line(
                journal, name, self, product, workorder=line.work_order,
                qty=qty, estim_std=-(qty * product.manual_standard_cost),
                estim_avg=-(qty * product.cost_price))
            analytic_line_obj.create(vals)
        journal = production.env.ref('mrp_production_project_estimated_cost.'
                                 'analytic_journal_machines', False)
        for line in production.workcenter_lines:
            op_wc_lines = line.routing_wc_line.op_wc_lines
            wc = op_wc_lines.filtered(lambda r: r.workcenter ==
                                      line.workcenter_id) or \
                line.workcenter_id
            if (wc.time_start and line.workcenter_id.pre_op_product):
                name = (_('%s-%s Pre-operation') %
                        (production.name, line.workcenter_id.name))
                product = line.workcenter_id.pre_op_product
                amount = product.cost_price * wc.time_start
                qty = wc.time_start
                vals = self._prepare_cost_analytic_line(
                    journal, name, self, product, workorder=line,
                    qty=qty, amount=-amount,
                    estim_std=-(qty * product.manual_standard_cost),
                    estim_avg=-(amount))
                analytic_line_obj.create(vals)
            if (wc.time_stop and line.workcenter_id.post_op_product):
                name = (_('%s-%s Post-operation') %
                        (production.name, line.workcenter_id.name))
                product = line.workcenter_id.post_op_product
                amount = product.cost_price * wc.time_stop
                qty = wc.time_stop
                vals = self._prepare_cost_analytic_line(
                    journal, name, self, product, workorder=line,
                    qty=qty, amount=-amount,
                    estim_std=-(qty * product.manual_standard_cost),
                    estim_avg=-(amount))
                analytic_line_obj.create(vals)
            if line.cycle and line.workcenter_id.costs_cycle:
                if not line.workcenter_id.product_id:
                    raise exceptions.Warning(
                        _("There is at least this workcenter without "
                          "product: %s") % line.workcenter_id.name)
                name = (_('%s-%s-C-%s') %
                        (production.name, line.routing_wc_line.operation.code,
                         line.workcenter_id.name))
                product = line.workcenter_id.product_id
                estim_cost = -(line.workcenter_id.costs_cycle * line.cycle) *  self.product_uom_qty
                vals = self._prepare_cost_analytic_line(
                    journal, name, self, product, workorder=line,
                    qty=line.cycle, estim_std=estim_cost,
                    estim_avg=estim_cost)
                analytic_line_obj.create(vals)
            if line.hour and line.workcenter_id.costs_hour:
                if not line.workcenter_id.product_id:
                    raise exceptions.Warning(
                        _("There is at least this workcenter without "
                          "product: %s") % line.workcenter_id.name)
                name = (_('%s-%s-H-%s') %
                        (production.name, line.routing_wc_line.operation.code,
                         line.workcenter_id.name))
                hour = line.hour *  self.product_uom_qty
                if wc.time_stop and not line.workcenter_id.post_op_product:
                    hour += wc.time_stop
                if wc.time_start and not line.workcenter_id.pre_op_product:
                    hour += wc.time_start
                estim_cost = -(hour * line.workcenter_id.costs_hour)
                vals = self._prepare_cost_analytic_line(
                    journal, name, self, line.workcenter_id.product_id,
                    workorder=line, qty=hour,
                    estim_std=estim_cost, estim_avg=estim_cost)
                analytic_line_obj.create(vals)
            if wc.op_number > 0 and line.hour:
                if not line.workcenter_id.product_id:
                    raise exceptions.Warning(
                        _("There is at least this workcenter without "
                          "product: %s") % line.workcenter_id.name)
                journal = production.env.ref(
                    'mrp_production_project_estimated_cost.analytic_'
                    'journal_operators', False)
                name = (_('%s-%s-%s') %
                        (production.name, line.routing_wc_line.operation.code,
                         line.workcenter_id.product_id.name))
                estim_cost = -(wc.op_number * wc.op_avg_cost * line.hour) * self.product_uom_qty
                qty = line.hour * wc.op_number * self.product_uom_qty
                
                vals = self._prepare_cost_analytic_line(
                    journal, name, self, line.workcenter_id.product_id,
                    workorder=line, qty=qty, estim_std=estim_cost,
                    estim_avg=estim_cost)
                analytic_line_obj.create(vals)
        analytic_line_obj.env.cr.commit()
        return True
    
    @api.multi                
    def _prepare_cost_analytic_line(self, journal, name, sale_line_id, product,
                                    general_account=None, workorder=None,
                                    qty=1, amount=0, estim_std=0, estim_avg=0):
        analytic_line_obj = self.env['account.analytic.line']
        property_obj = self.env['ir.property']
        if not general_account:
            general_account = (product.property_account_income or
                               product.categ_id.property_account_income_categ
                               or property_obj.get(
                                   'property_account_expense_categ',
                                   'product.category'))
        if not self.order_id.project_id:
            raise exceptions.Warning(
                _('You must define one Project for this Sale Order Quote: %s') %
                (self.order_id.name))
        vals = {
            'name': name,
            'sale_line_id': sale_line_id and sale_line_id.id or False,
            'workorder': workorder and workorder.id or False,
            'account_id': self.order_id.project_id.id,#Analytic Account ID
            'journal_id': journal.id,
            'user_id': self.env.uid,
            'date': analytic_line_obj._get_default_date(),
            'product_id': product and product.id or False,
            'unit_amount': qty,
            'amount': amount,
            'product_uom_id': product and product.uom_id.id or False,
            'general_account_id': general_account.id,
            'estim_std_cost': estim_std,
            'estim_avg_cost': estim_avg,
        }
        return vals
    
    
    @api.multi
    def get_production_sale_line_price(self):
        
        self.calculate_production_estimated_cost()
     
        analytic_line_obj = self.env['account.analytic.line']
        analytic_lines = analytic_line_obj.search([('sale_line_id','=',self.id)])
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
            [('sale_line_id', '=', self.id),
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
    def product_id_change(self, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False):
        
        res = super(sale_order_line, self).product_id_change(pricelist, product, qty=qty,
            uom=uom, qty_uos=qty_uos, uos=uos, name=name, partner_id=partner_id,
            lang=lang, update_tax=update_tax, date_order=date_order, packaging=packaging, fiscal_position=fiscal_position, flag=flag)
        
        if self.production_id:
            
            prices = self.get_production_sale_line_price()
            res['value']['purchase_price'] = prices.get('purchase_price',0.0)
            res['value']['production_avg_cost'] = prices.get('production_avg_cost',0.0)
            res['value']['price_unit'] = prices.get('price_unit',0.0)
          
        return res
            

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
 

        