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

import time
import eventor.vrpdb as rp
from acris import threaded
from acrilog import create_stream_handler
from datetime import datetime
import logging

logger=logging.getLogger()
handler=create_stream_handler(logging_level=logging.DEBUG)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

class MyResource1(rp.Resource): pass
class MyResource2(rp.Resource): pass

db_pool=rp.ResourcePool()

rp1=rp.ResourcePool('RP1', resource_cls=MyResource1, policy={'resource_limit': 1, }).load()                   
rp2=rp.ResourcePool('RP2', resource_cls=MyResource2, policy={'resource_limit': 1, }).load()

@threaded
def worker_awaiting(name, rp):
    print('[ %s ] %s getting resource' % (str(datetime.now()), name ) )
    r=rp.get()
    print('[ %s ] %s doing work (%s)' % (str(datetime.now()), name, repr(r)))
    time.sleep(1)
    print('[ %s ] %s returning %s' % (str(datetime.now()), name, repr(r)))
    rp.put(*r)
    

r1=worker_awaiting('>>> w1-direct', rp1)    
r2=worker_awaiting('>>> w2-direct', rp2)    
r3=worker_awaiting('>>> w3-direct', rp2)    
r4=worker_awaiting('>>> w4-direct', rp1) 



