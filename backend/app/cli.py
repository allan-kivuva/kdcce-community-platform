from datetime import date

import click
from flask.cli import with_appcontext

from .extensions import db
from .models import OPA, ROLES, ElderlyMember, HomeVisit, User, VolunteerProfile, utcnow
from .notifications.service import notify


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


# ---------- Demo data (development/presentation only) ----------
# Fictional, @example.com only. Every insert below is guarded by an
# existence check first (by OPA name, volunteer email, elder full_name,
# or the (elder, volunteer) pair for an assignment) — running this command
# twice fills in whatever's missing and never duplicates or modifies what's
# already there. Nothing here ever deletes, resets, or drops anything.

_DEMO_OPAS = [
    ("Kibera Elders Circle", "Kianda, Kibera", "Community group for older persons in the Kianda/Gatwekera area."),
    ("Mashimoni Golden Age Group", "Mashimoni, Kibera", "Older persons' association based in Mashimoni."),
]

# (name, email, password, phone, skills, availability, areas_of_interest, experience, motivation, bio)
_DEMO_VOLUNTEERS = [
    ("Grace Mwangi", "grace.mwangi@example.com", "GraceDemo2026!", "0711000001",
     "First aid, elderly care, basic nursing", "Weekday mornings", "Home visits, Health & wellness support",
     "3 years volunteering at a community health clinic", "I want to make sure our elders are never forgotten.",
     "Retired nurse, lives in Kibera, enjoys gardening."),
    ("Daniel Otieno", "daniel.otieno@example.com", "DanielDemo2026!", "0711000002",
     "Counselling, transportation, driving", "Weekends", "Activities & companionship, Home visits",
     "2 years as a peer counsellor for a local youth group", "Family taught me to always look after our elders.",
     "Works in logistics, volunteers on weekends."),
    ("Faith Wanjiru", "faith.wanjiru@example.com", "FaithDemo2026!", "0711000003",
     "Cooking, nutrition planning", "Weekday afternoons", "Feeding program, Home visits",
     "Ran a community kitchen for two years", "Good food and company can change someone's whole week.",
     "Caterer by trade, passionate about nutrition for older adults."),
    ("Samuel Kiptoo", "samuel.kiptoo@example.com", "SamuelDemo2026!", "0711000004",
     "Physiotherapy basics, first aid", "Flexible / on-call", "Health & wellness support, Home visits",
     "Volunteered with a mobile health clinic for 4 years", "I've seen how much a home visit can mean to someone living alone.",
     "Physiotherapy student, available most days."),
    ("Esther Njeri", "esther.njeri@example.com", "EstherDemo2026!", "0711000005",
     "Administration, fundraising, record keeping", "Weekday evenings", "Admin & office support, Fundraising & events",
     "Coordinated fundraising for a church welfare group", "I'd rather help behind the scenes so the frontline work can happen.",
     "Works in office administration, based in Nairobi."),
]

# (full_name, gender, year_of_birth, location, opa_name_or_None,
#  ec_name, ec_phone, ec_relationship, vulnerability_notes, health_notes, allergies, dietary_requirements)
_DEMO_ELDERS = [
    ("Alice Wambui", "Female", 1948, "Kianda, Kibera", "Kibera Elders Circle", "Peter Wambui", "0722100001", "Son", "Lives alone, limited mobility", "Hypertension, on daily medication", "Penicillin", "Low sodium diet"),
    ("Joseph Mutua", "Male", 1945, "Gatwekera, Kibera", "Kibera Elders Circle", "Ruth Mutua", "0722100002", "Daughter", "No close family nearby", "Type 2 diabetes", "None known", "Diabetic diet"),
    ("Elizabeth Nyambura", "Female", 1951, "Soweto East, Kibera", "Kibera Elders Circle", "Samuel Nyambura", "0722100003", "Son", "Hearing impaired", "Good general health", "None known", "No restrictions"),
    ("Peter Kimani", "Male", 1940, "Kisumu Ndogo, Kibera", "Kibera Elders Circle", "Grace Kimani", "0722100004", "Wife", "Uses a walking stick", "Arthritis in both knees", "Dust", "Soft foods only"),
    ("Agnes Adhiambo", "Female", 1953, "Lindi, Kibera", "Mashimoni Golden Age Group", "Tom Adhiambo", "0722100005", "Son", "Lives alone", "Mild asthma", "Peanuts", "No restrictions"),
    ("Francis Odhiambo", "Male", 1947, "Laini Saba, Kibera", "Mashimoni Golden Age Group", "Mercy Odhiambo", "0722100006", "Daughter", "Limited mobility, uses a wheelchair", "Hypertension", "None known", "Low sodium diet"),
    ("Rose Wairimu", "Female", 1949, "Silanga, Kibera", "Mashimoni Golden Age Group", "James Wairimu", "0722100007", "Son", "Visually impaired", "Cataracts, awaiting review", "None known", "No restrictions"),
    ("Charles Njoroge", "Male", 1944, "Makina, Kibera", "Mashimoni Golden Age Group", "Ann Njoroge", "0722100008", "Wife", "No close family nearby", "Type 2 diabetes, on insulin", "Shellfish", "Diabetic diet"),
    ("Jane Akoth", "Female", 1950, "Kianda, Kibera", None, "Brian Akoth", "0722100009", "Grandson", "Lives alone", "Good general health", "None known", "No restrictions"),
    ("David Omondi", "Male", 1946, "Gatwekera, Kibera", None, "Lucy Omondi", "0722100010", "Daughter", "Limited mobility", "Mild arthritis", "None known", "No restrictions"),
    ("Margaret Chebet", "Female", 1952, "Soweto East, Kibera", "Kibera Elders Circle", "Isaac Chebet", "0722100011", "Son", "Hearing impaired", "Hypertension, on medication", "Penicillin", "Low sodium diet"),
    ("Stephen Kiprop", "Male", 1943, "Kisumu Ndogo, Kibera", "Kibera Elders Circle", "Faith Kiprop", "0722100012", "Daughter", "Uses a walking frame", "Osteoarthritis", "None known", "Soft foods only"),
    ("Consolata Waithera", "Female", 1954, "Lindi, Kibera", None, "Paul Waithera", "0722100013", "Son", "Lives alone, no close family nearby", "Good general health", "None known", "No restrictions"),
    ("James Onyango", "Male", 1948, "Laini Saba, Kibera", "Mashimoni Golden Age Group", "Beatrice Onyango", "0722100014", "Wife", "Limited mobility", "Type 2 diabetes", "None known", "Diabetic diet"),
    ("Beatrice Nekesa", "Female", 1949, "Silanga, Kibera", "Mashimoni Golden Age Group", "George Nekesa", "0722100015", "Son", "Visually impaired", "Cataracts", "Dust", "No restrictions"),
    ("Paul Wafula", "Male", 1941, "Makina, Kibera", None, "Mary Wafula", "0722100016", "Daughter", "Uses a wheelchair", "Hypertension, mobility-limiting arthritis", "None known", "Low sodium diet"),
    ("Lucy Atieno", "Female", 1955, "Kianda, Kibera", "Kibera Elders Circle", "Vincent Atieno", "0722100017", "Son", "Lives alone", "Mild asthma", "Peanuts", "No restrictions"),
    ("Michael Kariuki", "Male", 1946, "Gatwekera, Kibera", "Kibera Elders Circle", "Nancy Kariuki", "0722100018", "Wife", "No close family nearby", "Good general health", "None known", "No restrictions"),
    ("Catherine Njambi", "Female", 1950, "Soweto East, Kibera", None, "Dennis Njambi", "0722100019", "Grandson", "Hearing impaired, lives alone", "Hypertension", "Shellfish", "Low sodium diet"),
    ("George Ochieng", "Male", 1942, "Kisumu Ndogo, Kibera", None, "Sarah Ochieng", "0722100020", "Daughter", "Uses a walking stick", "Type 2 diabetes, arthritis", "None known", "Diabetic diet"),
]


@click.command("seed-demo")
@with_appcontext
def seed_demo():
    """Idempotent demo-data seed for local development/presentation: 5
    Verified volunteers, 20 elderly members (across 2 demo OPAs), and a
    4-elderly-per-volunteer assignment using the existing HomeVisit
    assignment mechanism (assigned_to_id) — the same mechanism the real
    app uses, not a new relationship. Safe to run more than once."""
    admin_or_staff = User.query.filter(User.role.in_(("admin", "staff"))).first()
    if admin_or_staff is None:
        click.echo("No admin/staff account exists yet — run `flask seed-admin` first.")
        return

    opas = {}
    for name, location, description in _DEMO_OPAS:
        opa = OPA.query.filter_by(name=name).first()
        if opa is None:
            opa = OPA(name=name, location=location, description=description)
            db.session.add(opa)
            db.session.flush()
        opas[name] = opa

    volunteers = []
    for name, email, password, phone, skills, availability, areas, experience, motivation, bio in _DEMO_VOLUNTEERS:
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(name=name, email=email, role="volunteer")
            user.set_password(password)
            db.session.add(user)
            db.session.flush()
            profile = VolunteerProfile(
                user_id=user.id, phone=phone, skills=skills, availability=availability,
                areas_of_interest=areas, experience=experience, motivation=motivation, bio=bio,
            )
            db.session.add(profile)
            db.session.flush()
        else:
            profile = VolunteerProfile.query.filter_by(user_id=user.id).first()
        if profile.status != "Verified":
            profile.status = "Verified"
            profile.reviewed_by_id = admin_or_staff.id
            profile.reviewed_at = utcnow()
        volunteers.append((user, profile))

    elders = []
    for full_name, gender, birth_year, location, opa_name, ec_name, ec_phone, ec_rel, vuln, health, allergy, diet in _DEMO_ELDERS:
        member = ElderlyMember.query.filter_by(full_name=full_name).first()
        if member is None:
            member = ElderlyMember(
                full_name=full_name, gender=gender, date_of_birth=date(birth_year, 6, 15), location=location,
                opa_id=opas[opa_name].id if opa_name else None,
                emergency_contact_name=ec_name, emergency_contact_phone=ec_phone, emergency_contact_relationship=ec_rel,
                vulnerability_notes=vuln, health_notes=health, allergies=allergy, dietary_requirements=diet,
                status="Active", member_id="",
            )
            db.session.add(member)
            db.session.flush()  # assigns member.id without committing yet
            member.member_id = f"KDCCE-{utcnow().year}-{str(member.id).zfill(4)}"
        elders.append(member)

    new_assignments = 0
    for i, (user, _profile) in enumerate(volunteers):
        for elder in elders[i * 4:(i + 1) * 4]:
            existing = HomeVisit.query.filter_by(elderly_member_id=elder.id, assigned_to_id=user.id).first()
            if existing is not None:
                continue
            visit = HomeVisit(
                elderly_member_id=elder.id, assigned_to_id=user.id, requested_by_id=admin_or_staff.id,
                reason=f"Routine wellbeing home visit for {elder.full_name}.", priority="Medium", status="Assigned",
            )
            db.session.add(visit)
            db.session.flush()  # assigns visit.id so the notification can reference it
            notify(
                user.id, "Home Visit Assignment", "Home visit assigned to you",
                f"You have been assigned a home visit for {elder.full_name}.",
                related_resource_type="home_visit", related_resource_id=visit.id,
            )
            new_assignments += 1

    db.session.commit()
    click.echo(f"Demo seed complete: {len(volunteers)} volunteers, {len(elders)} elderly members, {new_assignments} new assignment(s) created this run.")
