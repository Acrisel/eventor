'''
Created on Oct 21, 2016

@author: arnon
'''

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
import logging
import os
import threading
from datetime import datetime

from .dbschema import task_table, trigger_table, delay_table, info_table
from .dbschema import trigger_from_db, task_from_db, delay_from_db
from .eventor_types import DbMode
from .utils import decorate_all, print_method, calling_module
from .sqladburl import SQLAlchemyConf

mlogger = logging.getLogger(__name__)


class DbApiError(Exception):
    pass


def get_sqlalchemy_conf(modulefile, userstore, config, root=None, echo=False, logger=None):
    '''
        If userstore is provided:
            If it is a database key in config:
                use that database
            elif ':memory:':
                use in-memory
            else:
                use as runfile
        elif database has default key:
            use default database
        elif modulefile  is provided:
            use modulefile
        else:
            use memory
    '''
    global mlogger
    if logger:
        mlogger = mlogger

    if not root:
        root = os.environ.get('EVENTOR_DB_CONFIG_TAG', 'DATABASES')

    database = userstore if userstore else 'default'
    try:
        sqldb = SQLAlchemyConf(conf=config, root=root, database=database, quiet=False, echo=echo, logger=mlogger)
    except Exception:
        if userstore == ':memory:':
            conf = {'DB': {'adhoc': {'dialect': 'sqlite', 'query': {'cache': 'shared'}}}}
        elif userstore:
            conf = {'DB': {'adhoc': {'dialect': 'sqlite', 'database': userstore}}}
        elif modulefile:
            conf = {'DB': {'adhoc': {'dialect': 'sqlite', 'database': modulefile}}}
        else:
            conf = {'DB': {'adhoc': {'dialect': 'sqlite', 'query': {'cache': 'shared'}}}}

        mlogger.debug("DBAPI: Using adhoc DB config: %s" % (repr(conf)))
        sqldb = SQLAlchemyConf(conf=conf, root='DB', database='adhoc', quiet=True, echo=echo, logger=mlogger)
    else:
        mlogger.debug("DBAPI: Using DB config: %s" % (repr(config)))

    mlogger.debug("DBAPI: SQLAlchemyConf: %s" % (repr(sqldb),))
    return sqldb


class DbApi(object):

    def __init__(self, modulefile=None, shared_db=False, run_id='', userstore=None, session=None, mode=DbMode.write, config={}, root=None, thread_sync=False, create=True, echo=False, logger=None):
        '''
        Args:
            moduefile (path): file in which Eventor data would be stored and managed for reply/restart
            if the value is :memory:, an in-memory temporary structures will be used
            userstore (path): store file provided by user
            create: if not set, assume already created and used in this session, skip create.
        Devising storage:
            If Store is provided:
                If it is a database key in config:
                    use that database
                else:
                    use as runfile
            else:
                if database has default key:
                    use default database
                else:
                    use modulefile if provided
        '''
        global mlogger
        if logger:
            mlogger = logger

        self.engine = None
        self.session = None
        self.run_id = run_id
        self.shared_db = shared_db
        self.thread_sync = thread_sync

        self.__sqlalchemy = get_sqlalchemy_conf(modulefile, userstore, config,
                                                root=root, echo=echo)
        self.metadata = metadata = self.__sqlalchemy.get_metadata()

        Base = declarative_base(metadata=metadata)
        self.Info = info_table(Base)
        self.Task = task_table(Base)
        self.Delay = delay_table(Base)
        self.Trigger = trigger_table(Base)

        if session:
            self.session = session()
        else:
            self.session = self.__sqlalchemy.get_session(force=True, autocommit=False)
        self.open(mode=mode, create=create)

    def set_thread_synchronization(self, value=True):
        self.thread_sync = value

    def lock(self):
        if self.thread_sync:
            self.db_transaction_lock.acquire()

    def release(self):
        if self.thread_sync:
            self.db_transaction_lock.release()

    def open(self, mode=DbMode.write, create=True):
        self.db_transaction_lock = threading.Lock()
        if mode == DbMode.write and create:
            mlogger.debug("DBAPI: DbMode write: creating schema and tables.")
            self.create_db()

    def close(self):
        self.session.close()
        self.db_transaction_lock = None

    def create_schema(self):
        metadata = self.metadata
        schemas = set()
        for table in metadata.tables.values():
            if table.schema is not None:
                schemas.add(table.schema)

        if len(schemas) > 0:
            for schema in schemas:
                if not self.shared_db:
                    mlogger.debug("DBAPI: Not in shared_db mode: dropping before creating"
                                  " schema %s." % (schema))
                    metadata.bind.execute("DROP SCHEMA IF EXISTS %s CASCADE" % schema)
                metadata.bind.execute("CREATE SCHEMA IF NOT EXISTS %s" % schema)
        '''
        elif self.__sqlalchemy.dbconf['dialect'] == 'sqlite':
            # in this case we need to remove database
            if not self.shared_db:
                # TODO: (arnon) with self.shared_db False, logging filter is being override.
                #    once solved, can allow self.sharec_db True
                database = self.__sqlalchemy.dbconf.get('database')
                if database is not None:
                    if os.path.isfile(database):
                        mlogger.debug("DBAPI: Not in shared_db mode: removing database"
                                      " file: %s." % (database))
                        os.remove(database)
        '''

    def create_db(self, ):
        # self.__create_engine(runfile)
        self.create_schema()
        if not self.shared_db:
            self.metadata.drop_all()
        self.metadata.create_all()
        self.session.commit()

    def commit_db(self):
        self.session.flush()
        self.session.commit()

    def rollback_db(self):
        self.session.rollback()

    def write_info(self, **info):
        self.lock()
        for name, value in info.items():
            db_info = self.Info(run_id=self.run_id, name=name, value=value)
            self.session.add(db_info)
        self.commit_db()
        self.release()

    def read_info(self, ):
        self.lock()
        rows = self.session.query(self.Info).filter(self.Info.run_id == self.run_id).all()
        self.session.commit()
        self.release()
        info = dict()
        for row in rows:
            info[row.name] = row.value
        return info

    def update_info(self, **info):
        self.lock()
        for name, value in info.items():
            self.session.query(self.Info)\
                .filter(self.Info.run_id == self.run_id, self.Info.name == name)\
                .update({self.Info.name: name, self.Info.value: value}, synchronize_session=False)
        self.commit_db()
        self.release()

    def get_trigger_iter(self, recovery):
        self.lock()
        rows = self.session.query(self.Trigger).filter(self.Trigger.run_id == self.run_id,
                                                       self.Trigger.recovery == recovery).all()
        # rows = query.statement.execute().fetchall()
        self.session.commit()
        self.release()
        for row in rows:
            yield trigger_from_db(row)
        # return rows

    def get_trigger_map(self, recovery=0):
        self.lock()
        triggers = self.session.query(self.Trigger).filter(self.Trigger.run_id == self.run_id,
                                                           self.Trigger.recovery == recovery).all()
        self.session.commit()
        self.release()
        trigger_map = dict()
        for trigger in triggers:
            try:
                sequence_map = trigger_map[trigger.sequence]
            except KeyError:
                sequence_map = dict()
                trigger_map[trigger.sequence] = sequence_map
            sequence_map[trigger.event_id] = trigger_from_db(trigger)
        return trigger_map

    def add_trigger(self, event_id, sequence, recovery):
        trigger = self.Trigger(run_id=self.run_id, event_id=event_id, sequence=sequence, recovery=recovery)
        self.lock()
        self.session.add(trigger)
        self.commit_db()
        self.release()
        mlogger.debug("DBAPI: add_trigger: {}.".format(trigger,))
        return trigger_from_db(trigger)

    def add_trigger_if_not_exists(self, event_id, sequence, recovery):
        self.lock()
        # TODO: (Arnon) since distributed, need to change to either "select for update" or
        #    "on duplicate key update"
        # self.session.begin()
        mlogger.debug("DBAPI: checking if event trigger do not exist: {}({})."
                      .format(event_id, sequence))
        try:
            trigger = self.session.query(self.Trigger).filter(self.Trigger.run_id == self.run_id,
                                                              self.Trigger.event_id == event_id,
                                                              self.Trigger.sequence == str(sequence),
                                                              self.Trigger.recovery == recovery)
            found = self.session.query(trigger.exists()).scalar()
        except Exception:
            # self.commit_db()
            self.release()
            raise
        if not found:
            mlogger.debug("DBAPI: adding event trigger {}({}).".format(event_id, sequence))
            trigger = self.Trigger(run_id=self.run_id, event_id=event_id, sequence=str(sequence),
                                   recovery=recovery)
            self.session.add(trigger)
            try:
                self.commit_db()
            except IntegrityError:
                self.rollback_db()
                found = self.session.query(self.Trigger).filter(self.Trigger.run_id == self.run_id,
                                                                self.Trigger.event_id == event_id,
                                                                self.Trigger.sequence == str(sequence),
                                                                self.Trigger.recovery == recovery)
                trigger = found.first()
                mlogger.debug("DBAPI: trigger already in db, returning {}; {}."
                              .format(found, trigger))
        else:
            trigger = trigger.first()
            mlogger.debug("DBAPI: skip insert, trigger already in db, returning {}; {}."
                          .format(found, trigger))
            self.commit_db()
        self.release()
        return trigger_from_db(trigger)

    def _get_trigger(self, trigger):
        rows = self.session.query(self.Trigger).filter(self.Trigger.id_ == trigger.id_).all()
        self.session.commit()
        try:
            return rows[0]
        except Exception:
            return None

    def acted_trigger(self, trigger):
        self.lock()
        db_trigger = self._get_trigger(trigger)
        trigger.acted = db_trigger.acted = datetime.utcnow()
        # self.session.add(trigger)
        self.commit_db()
        self.release()
        mlogger.debug("DBAPI: acted_trigger: {}.".format(trigger,))
        return trigger

    def count_trigger_ready(self, sequence=None, recovery=None):
        self.lock()
        members = self.session.query(self.Trigger)\
                      .filter(self.Trigger.run_id == self.run_id,
                              # Note: qlalchemy uses magic methods (operator overloading) to create
                              # SQL constructs, it can only handle operator such as != or ==, but
                              # is not able to work with is (which is a very valid Python
                              # construct).
                              self.Trigger.acted == None,
                              self.Trigger.recovery == recovery)
        if sequence:
            members = members.filter(self.Trigger.sequence == str(sequence))
        count = members.count()
        self.session.commit()
        self.release()
        return count

    def count_trigger_ready_like(self, sequence, recovery):
        self.lock()
        try:
            members = self.session.query(self.Trigger)\
                          .filter(self.Trigger.sequence.like(str(sequence)),
                                  self.Trigger.run_id == self.run_id,
                                  # Note: qlalchemy uses magic methods (operator overloading) to
                                  # create SQL constructs, it can only handle operator such as
                                  # != or ==, but is not able to work with is (which is a very
                                  # valid Python construct).
                                  self.Trigger.acted == None,
                                  self.Trigger.recovery == recovery)
        except Exception:
            self.session.commit()
            self.release()
            raise
        count = members.count()
        self.session.commit()
        self.release()
        return count

    def add_task(self, step_id, sequence, host, status, recovery=None):
        self.lock()
        task = self.Task(run_id=self.run_id, step_id=step_id, sequence=str(sequence), host=host,
                         status=status, recovery=recovery)
        self.session.add(task)
        self.commit_db()
        self.release()
        return task_from_db(task)

    def add_task_if_not_exists(self, step_id, sequence, host, status, recovery=None):
        self.lock()
        # TODO: (Arnon) since distributed, need to change to either "select for update"
        #      or "on duplicate key update"
        # self.session.begin()
        task = self.session.query(self.Task).filter(self.Task.run_id == self.run_id,
                                                    self.Task.sequence == str(sequence),
                                                    self.Task.host == host,
                                                    self.Task.step_id == step_id,
                                                    self.Task.recovery == recovery)
        found = self.session.query(task.exists()).scalar()
        if not found:
            # it still may be that remote would inserted
            task = self.Task(run_id=self.run_id, step_id=step_id, sequence=sequence, host=host,
                             status=status, recovery=recovery)
            self.session.add(task)
            try:
                self.commit_db()
            except IntegrityError:
                self.rollback_db()
                found = self.session.query(self.Task).filter(self.Task.run_id == self.run_id,
                                                             self.Task.sequence == str(sequence),
                                                             self.Task.host == host,
                                                             self.Task.step_id == step_id,
                                                             self.Task.recovery == recovery)
                task = found.first()
                mlogger.debug("DBAPI: task already in db, returning {}; {}.".format(found, task,))
        else:
            task = task.first()
            mlogger.debug("DBAPI: skip insert, task already in db, returning {}; {}.".format(found, task))
        self.commit_db()
        self.release()
        result = task_from_db(task)
        mlogger.debug('DBAPI: add_task_if_not_exists: {}'.format(repr(result), ))
        return result

    def update_task(self, task, session=None):
        self.lock()
        if not session:
            session = self.session
        task.updated = updated = datetime.utcnow()
        updates = {self.Task.status: task.status, self.Task.updated: updated}
        if task.pid:
            updates[self.Task.pid] = task.pid
        if task.result:
            updates[self.Task.result] = task.result
        try:
            self.session.query(self.Task).filter(self.Task.id_ == task.id_)\
                .update(updates, synchronize_session=False)
        except Exception:
            raise

        self.commit_db()
        self.release()
        mlogger.debug('DBAPI: update_task: %s' % (repr(task), ))
        return task

    def update_task_status(self, task, status, session=None,):
        self.lock()

        task_id = task.id_

        if not session:
            session = self.session
        task.updated = updated = datetime.utcnow()
        task.status = status
        mlogger.debug('DBAPI: updating task status: %s(%s)' % (task_id, status))
        updates = {self.Task.status: status, self.Task.updated: updated}
        self.session.query(self.Task).filter(self.Task.id_ == task_id)\
            .update(updates, synchronize_session=False)
        self.commit_db()
        self.release()
        return task

    def get_task_iter(self, recovery, host=None, status=None):
        # TODO: do we really need recovery here
        self.lock()
        # rows = self.session.query(self.Task)
        dbrows = self.session.query(self.Task).filter(self.Task.run_id == self.run_id)
        if status:
            dbrows = dbrows.filter(self.Task.status.in_(status))
        if host:
            dbrows = dbrows.filter(self.Task.host == host)

        dbrows = dbrows.all()
        rows = [task_from_db(row) for row in dbrows]
        self.session.commit()
        self.release()

        for result in rows:
            # result = task_from_db(row)
            mlogger.debug("DBAPI: task_iter: task: %s" % (repr(result)))
            yield result

    def get_task_map(self, recovery=0):
        self.lock()
        tasks = self.session.query(self.Task).filter(self.Task.run_id == self.run_id,
                                                     self.Task.recovery == recovery).all()
        task_map = dict()
        for task in tasks:
            try:
                sequence_map = task_map[task.sequence]
            except KeyError:
                sequence_map = dict()
                task_map[task.sequence] = sequence_map
            sequence_map[task.step_id] = task_from_db(task)
        self.session.commit()
        self.release()
        mlogger.debug("DBAPI: get_task_map: task: %s" % (repr(task_map)))
        return task_map

    def count_tasks(self, recovery, status, sequence=None, host=None):
        self.lock()
        with self.session.no_autoflush:
            members = self.session.query(self.Task)
        members = members.filter(self.Task.run_id == self.run_id,
                                 self.Task.status.in_(status),
                                 self.Task.recovery == recovery)
        if sequence:
            members = members.filter(self.Task.sequence == str(sequence))
        if host:
            members = members.filter(self.Task.host == host)
        count = members.count()
        self.session.commit()
        self.release()
        return count

    def count_tasks_like(self, sequence, recovery, status):
        self.lock()
        with self.session.no_autoflush:
            members = self.session.query(self.Task).filter(self.Task.run_id == self.run_id,
                                                           self.Task.sequence.like(str(sequence)),
                                                           self.Task.status.in_(status),
                                                           self.Task.recovery == recovery)
        all_ = members.all()
        tasks = ["{}/{}".format(task.step_id, task.sequence) for task in all_]
        mlogger.debug("DBAPI: count_tasks_like: tasks: {}.".format(repr(tasks)))
        count = members.count()
        self.session.commit()
        self.release()
        return count

    def get_task_status(self, task_names, sequence, host, recovery):
        self.lock()
        try:
            tasks = self.session.query(self.Task).filter(self.Task.run_id == self.run_id,
                                                         self.Task.step_id.in_(task_names),
                                                         self.Task.sequence == str(sequence),
                                                         self.Task.host == host,
                                                         self.Task.recovery == recovery).all()
        except Exception:
            raise
        result = dict()
        for task in tasks:
            result[task.step_id] = task.status
        self.session.commit()
        self.release()
        mlogger.debug("DBAPI: get_task_status: task: {}".format(repr(result)))
        return result

    def add_delay(self, delay_id, sequence, seconds, active=None, activated=None, recovery=None):
        delay = self.Delay(run_id=self.run_id, delay_id=delay_id, seconds=seconds,
                           sequence=str(sequence), recovery=recovery,)
        mlogger.debug('DBAPI: add_delay: {}'.format(repr(delay), ))
        self.lock()
        try:
            self.session.add(delay)
        except IntegrityError:
            self.release()
            raise
        self.commit_db()
        self.release()
        return delay_from_db(delay)

    def add_delay_update_if_not_exists(self, delay_id, sequence, seconds, active=None, activated=None, recovery=None):
        self.lock()
        delay = self.session.query(self.Delay).filter(self.Delay.run_id == self.run_id,
                                                      self.Delay.sequence == str(sequence),
                                                      self.Delay.delay_id == delay_id,
                                                      self.Delay.recovery == recovery)
        found = self. session.query(delay.exists()).scalar()
        if not found:
            delay = self.Delay(run_id=self.run_id, delay_id=delay_id, seconds=seconds,
                               sequence=str(sequence), recovery=recovery, active=active,
                               activated=activated)
            self.session.add(delay)
            self.commit_db()
            mlogger.debug("DBAPI: add new delay {}; {}.".format(found, delay,))
        else:
            delay = delay.first()
            if delay.active != active:
                if active:
                    delay.activated = datetime.utcnow()
                delay.active = active
                self.commit_db()
            mlogger.debug("DBAPI: delayed found, updating: {}; {}.".format(found, delay,))
        self.release()
        result = delay_from_db(delay)
        mlogger.debug("DBAPI: add_delay_update_if_not_exists result: {}.".format(delay,))
        return result

    def get_delay_map(self, recovery=0):
        self.lock()
        items = self.session.query(self.Delay).filter(self.Delay.run_id == self.run_id,
                                                      self.Delay.recovery == recovery).all()
        self.session.commit()
        self.release()
        item_map = dict()
        for item in items:
            try:
                sequence_map = item_map[item.sequence]
            except KeyError:
                sequence_map = dict()
                item_map[item.sequence] = sequence_map
            sequence_map[item.delay_id] = delay_from_db(item)
        return item_map

    def get_delay_iter(self, recovery, active=True):
        self.lock()
        rows = self.session.query(self.Delay).filter(self.Delay.run_id == self.run_id,
                                                     self.Delay.recovery == recovery).all()
        # rows = query.statement.execute().fetchall()
        self.session.commit()
        self.release()
        for row in rows:
            yield delay_from_db(row)

    def _get_delay(self, delay):
        # self.lock()
        rows = self.session.query(self.Delay).filter(self.Delay.id_ == delay.id_)
        # rows = query.statement.execute().fetchall()
        # self.release()
        self.session.commit()
        try:
            return rows[0]
        except Exception:
            return None

    def activate_delay(self, delay):
        self.lock()
        db_delay = self._get_delay(delay)
        delay.activated = db_delay.activated = datetime.utcnow()
        delay.active = True
        self.commit_db()
        self.release()
        mlogger.debug("DBAPI: activate_delay: {}.".format(delay,))
        return delay

    def deactivate_delay(self, delay):
        self.lock()
        db_delay = self._get_delay(delay)
        delay.active = db_delay.active=False
        self.commit_db()
        self.release()
        mlogger.debug("DBAPI: deactivate_delay: {}.".format(delay,))
        return delay

    def count_active_delays(self, sequence, recovery,):
        self.lock()
        with self.session.no_autoflush:
            members = self.session.query(self.Delay)
            members = members.filter(self.Delay.run_id == self.run_id,
                                     self.Delay.recovery == recovery,
                                     self.Delay.active.is_(True))

        now = datetime.utcnow()
        time_to_mature = [m.seconds-(now-m.activated).total_seconds() for m in members]
        min_time_to_mature = min(time_to_mature) if len(time_to_mature) > 0 else None
        count = members.count()
        self.session.commit()
        self.release()
        return count, min_time_to_mature


if __name__ == '__main__':
    import pickle
    # file='/var/acrisel/sand/eventor/eventor/eventor/eventor/schema.db'
    # file=':memory:'
    mydb = DbApi(userstore='sqfile', root='eventor.databases', config='dbapi.conf')
    # mydb.add_event(event_id='34', name='evently')
    mydb.commit_db()

    delay = mydb.add_delay(delay_id='mydelay', seconds=2419200, sequence=3, )
    print(repr(delay))
    delay = mydb.activate_delay(delay)
    print(repr(delay))
    delay = mydb.deactivate_delay(delay)
    print(repr(delay))
    mydb.commit_db()
    task = mydb.Task()
