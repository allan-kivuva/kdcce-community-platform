import click
from flask.cli import with_appcontext

from .extensions import db
from .models import ROLES, User


@click.command("seed-admin")
@click.option("--name", prompt=True)
@click.option("--email", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--role", type=click.Choice(ROLES), default="admin")
@with_appcontext
def seed_admin(name, email, password, role):
    """Create the first admin/staff account. There is no public signup
    endpoint for elevated roles on purpose — this is the only way to
    create one, and it's an operator running a local command, not
    something reachable over the network."""
    email = email.lower().strip()
    if User.query.filter_by(email=email).first():
        click.echo(f"A user with email {email} already exists.")
        return

    user = User(name=name.strip(), email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Created {role} user: {email}")
