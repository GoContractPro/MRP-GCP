# -*- encoding: utf-8 -*-
##############################################################################
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

from openerp import models, fields, api, _
import math

from openerp.addons.product import _common
from openerp import tools

class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    @api.multi
    @api.onchange('workcenter_id')
    def onchange_workcenter_id(self, workcenter_id):
        
        res={}
        res['value']={}
        
        if workcenter_id:
        
            wc = self.env['mrp.workcenter'].browse(workcenter_id)           
            res['value']['name'] = wc.name
                  
        return res
          
class mrp_production_workcenter_line(models.Model):
    _inherit = 'mrp.production.workcenter.line'
    
    
    @api.multi
    def _compute_next_sequence(self,production_id):
        
        cr = self.env.cr
        cr.execute('select max(sequence) from mrp_production_workcenter_line '
                   'where production_id = %s'
                    ,(production_id,) )
        max_sequence = cr.fetchone()
        
        return int(max_sequence[0]) + 10
     
            
    @api.one
    def write(self, vals, update=False):
          
        return super(mrp_production_workcenter_line, self).write(vals,update=update)
    
    @api.multi
    @api.onchange('cycle')
    def onchange_cycle(self, cycle, workcenter_id):
        
        res={}
        if workcenter_id:
            wc = self.env['mrp.workcenter'].browse(workcenter_id)
            
            res['value'] = {
                            'hour':wc.time_cycle * cycle
                            }
            
        return res
 
    @api.multi
    @api.onchange('workcenter_id')
    def onchange_workcenter_id(self, workcenter_id):
   
        
        res={}
        production_id = self.env.context.get('default_production_id')
        production = self.env['mrp.production'].browse(production_id)
        

        if workcenter_id:
            def _factor(factor, product_efficiency, product_rounding):
                factor = factor / (product_efficiency or 1.0)
                factor = _common.ceiling(factor, product_rounding)
                if factor < product_rounding:
                    factor = product_rounding
                return factor
    
            factor = _factor(production.product_qty, production.bom_id.product_efficiency, production.bom_id.product_rounding)
            
            wc = self.env['mrp.workcenter'].browse(workcenter_id)
            
            if  wc.capacity_per_cycle:
                d, m = divmod(factor, wc.capacity_per_cycle)
                cycle = (d + (m and 1.0 or 0.0))     
                hour = wc.time_cycle * cycle
                
            res['value'] = {    
                            'time_start':wc.time_start,
                            'time_stop':wc.time_stop,
                            'name':tools.ustr(wc.name) + ' - ' + tools.ustr(production.bom_id.product_tmpl_id.name_get()[0][1]),
                            'hour':hour,
                            'cycle':cycle,
                            }
 
        return res
    
    @api.model
    def default_get(self, var_fields):
            
 
        res = super(mrp_production_workcenter_line, self).default_get(
            var_fields) 
 
        production_id = self.env.context.get('default_production_id',False)
        if production_id:
            res['sequence'] = self._compute_next_sequence(production_id)
        
        return res 