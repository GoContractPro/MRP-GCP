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

class mrp_production_workcenter_line(models.Model):
    _inherit = 'mrp.production.workcenter.line'
    

    
    @api.one
    def write(self, vals, update=False):
          
        return super(mrp_production_workcenter_line, self).write(vals,update=update)
 
    @api.model
    @api.onchange('workcenter_id')
    def onchange_workcenter_id(self, workcenter_id):
   
        if workcenter_id:
            def _factor(factor, product_efficiency, product_rounding):
                factor = factor / (product_efficiency or 1.0)
                factor = _common.ceiling(factor, product_rounding)
                if factor < product_rounding:
                    factor = product_rounding
                return factor
    
            factor = _factor(self.production_id.product_qty, self.production_id.bom_id.product_efficiency, self.production_id.bom_id.product_rounding)
            
            wc = self.env['mrp.workcenter'].browse(workcenter_id)
            
            d, m = divmod(factor, wc.capacity_per_cycle)
            mult = (d + (m and 1.0 or 0.0))
       
            self.hour = self.workcenter.time_cycle
            self.time_start = self.workcenter.time_start
            self.time_stop = self.workcenter.time_stop
            self.cycle = mult
            self.name = tools.ustr(wc.name) + ' - ' + tools.ustr(self.production_id.product_tmpl_id.name_get()[0][1])