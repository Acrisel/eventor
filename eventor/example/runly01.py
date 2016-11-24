
# -*- encoding: utf-8 -*-
##############################################################################
#
#    Acrisel LTD
#    Copyright (C) 2008- Acrisel (acrisel.com) . All Rights Reserved
#
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
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################
"""

About
=========
:synopsis:     example use of grapior
:moduleauthor: Arnon Sela
:date:         Oct 18, 2016
:description:  use gradior dependencies and recovery
   
Outputs:
-------------------
N/A

Dependencies:
-------------------
N/A
      
**History:**
-------------------

:Author: Arnon Sela
:Modification:
   - Initial entry
:Date: Oct 18, 2016


API DOC:
===============     
"""

import eventor as evr
import logging
import example.program as prog

logger=logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)

ev=evr.Eventor(name='mine')

ev1=ev.add_event('run_step1')
ev2=ev.add_event('run_step2')

s1=ev.add_step('s11', func=prog.step1_create_data, func_kwargs={'outfile': 'source.txt'}) 
s2=ev.add_step('s12', prog.step2_multiple_data,)

ev.add_assoc(ev1, evr.AssocType.step, s1)
ev.add_assoc(ev1, evr.AssocType.step, s2)

ev.loop_once()
ev.raise_event(s1, 1)
ev.loop_once()
ev.raise_event(s1, 1)

