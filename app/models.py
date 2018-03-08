# -*- coding: utf8 -*-
from app import db


class GlobalMacro(db.Model):
    """
    存全局变量用到的key/value对.
    """
    __tablename__ = 'global_macros'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    global_macro_id = db.Column(db.Integer, primary_key=True)
    macro = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(1024))

    def __repr__(self):
        return '<GlobalMacro %s: %s>' % (self.macro, self.value)


class ServerMacro(db.Model):
    """
    存单个服务器的key/value对.
    """
    __tablename__ = 'server_macros'
    __table_args__ = {'mysql_charset': 'utf8', 'mysql_engine': 'InnoDB'}

    server_macro_id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('servers.id'))
    macro = db.Column(db.String(64), nullable=False)
    value = db.Column(db.String(1024))

    def __repr__(self):
        return '<ServerMacro %s: %s>' % (self.macro, self.value)
