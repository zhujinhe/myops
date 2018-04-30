#!/usr/bin/env python
# -*- coding: utf8 -*-
import os
from app import create_app, db
from flask_script import Manager, Shell
from flask_migrate import Migrate, MigrateCommand
from app.auth.models import User, Group, Policy
from app.assets.models import Server

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
manager = Manager(app)
migrate = Migrate(app, db)


def make_shell_context():
    return dict(app=app,
                db=db,
                User=User, Group=Group,
                Policy=Policy,
                Server=Server,
                p2=Policy.query.filter_by(policy_id=2).first()
                )


manager.add_command("shell", Shell(make_context=make_shell_context))
manager.add_command("db", MigrateCommand)


@manager.command
def test():
    pass


if __name__ == '__main__':
    manager.run()
