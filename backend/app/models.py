from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db

ROLES = ("admin", "staff", "volunteer")


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="volunteer")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
        }


DONATION_STATUSES = ("Paid", "Pending")
DONATION_FREQUENCIES = ("one-time", "monthly")


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    donor_name = db.Column(db.String(120), nullable=False)
    donor_email = db.Column(db.String(255), nullable=False)
    donor_phone = db.Column(db.String(40), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(8), nullable=False, default="KES")
    frequency = db.Column(db.String(20), nullable=False, default="one-time")
    campaign = db.Column(db.String(120), nullable=True)
    payment_method = db.Column(db.String(40), nullable=True)
    # NOTE: no real payment gateway is integrated in this project. "status"
    # is a workflow label the org uses internally, never a verified payment
    # confirmation. It is always server-set on creation (never taken from
    # the public-facing create request) and can only be changed afterward
    # by an authenticated admin/staff edit. See docs/donations.md.
    status = db.Column(db.String(20), nullable=False, default="Paid")
    txn_id = db.Column(db.String(60), unique=True, nullable=False)
    receipt_id = db.Column(db.String(60), unique=True, nullable=False)
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "donor_name": self.donor_name,
            "donor_email": self.donor_email,
            "donor_phone": self.donor_phone,
            "amount": float(self.amount),
            "currency": self.currency,
            "frequency": self.frequency,
            "campaign": self.campaign,
            "payment_method": self.payment_method,
            "status": self.status,
            "txn_id": self.txn_id,
            "receipt_id": self.receipt_id,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


BLOG_STATUSES = ("Published", "Draft")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    excerpt = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(500), nullable=True)
    type = db.Column(db.String(40), nullable=False, default="Story")
    status = db.Column(db.String(20), nullable=False, default="Draft")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "excerpt": self.excerpt,
            "image": self.image,
            "type": self.type,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    caption = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "url": self.url,
            "caption": self.caption,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


CRAFT_STATUSES = ("Available", "Reserved", "Sold")


class Craft(db.Model):
    __tablename__ = "crafts"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    maker = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Available")
    image = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "maker": self.maker,
            "price": float(self.price),
            "status": self.status,
            "image": self.image,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class OPA(db.Model):
    """Older Persons Association / community group an elderly member
    belongs to. Simple reference table — deleting one just clears the
    reference on any member that pointed to it (see the FK ondelete)."""

    __tablename__ = "opas"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    location = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


ELDERLY_GENDERS = ("Male", "Female", "Other")
ELDERLY_STATUSES = ("Active", "Inactive", "Deceased", "Transferred")


class ElderlyMember(db.Model):
    __tablename__ = "elderly_members"

    id = db.Column(db.Integer, primary_key=True)
    # KDCCE-<year>-<zero-padded id>, assigned server-side on creation —
    # same pattern as Donation.receipt_id. Never client-supplied.
    member_id = db.Column(db.String(30), unique=True, nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=False)
    location = db.Column(db.String(150), nullable=True)
    opa_id = db.Column(db.Integer, db.ForeignKey("opas.id", ondelete="SET NULL"), nullable=True)
    emergency_contact_name = db.Column(db.String(120), nullable=True)
    emergency_contact_phone = db.Column(db.String(40), nullable=True)
    emergency_contact_relationship = db.Column(db.String(60), nullable=True)
    # Sensitive: vulnerability/health/allergy notes. Every route reading or
    # writing this model requires admin/staff (see auth/decorators.py) —
    # volunteers have no access to elderly records at all, by design.
    vulnerability_notes = db.Column(db.Text, nullable=True)
    health_notes = db.Column(db.Text, nullable=True)
    allergies = db.Column(db.Text, nullable=True)
    dietary_requirements = db.Column(db.Text, nullable=True)
    registration_date = db.Column(db.Date, default=lambda: utcnow().date(), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Active")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    opa = db.relationship("OPA")

    def to_dict(self):
        return {
            "id": self.id,
            "member_id": self.member_id,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "location": self.location,
            "opa_id": self.opa_id,
            "opa_name": self.opa.name if self.opa else None,
            "emergency_contact_name": self.emergency_contact_name,
            "emergency_contact_phone": self.emergency_contact_phone,
            "emergency_contact_relationship": self.emergency_contact_relationship,
            "vulnerability_notes": self.vulnerability_notes,
            "health_notes": self.health_notes,
            "allergies": self.allergies,
            "dietary_requirements": self.dietary_requirements,
            "registration_date": self.registration_date.isoformat(),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Attendance(db.Model):
    """One row per check-in. check_out_at stays null until the member is
    checked out; attendance_date is stored separately from check_in_at (not
    derived) so a day's records are a plain indexed equality filter."""

    __tablename__ = "attendance_records"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    attendance_date = db.Column(db.Date, default=lambda: utcnow().date(), nullable=False, index=True)
    check_in_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    check_out_at = db.Column(db.DateTime(timezone=True), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "attendance_date": self.attendance_date.isoformat(),
            "check_in_at": self.check_in_at.isoformat(),
            "check_out_at": self.check_out_at.isoformat() if self.check_out_at else None,
            "recorded_by": self.recorded_by.name,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


WELLBEING_LEVELS = ("Good", "Fair", "Poor")


class HealthRecord(db.Model):
    """A single point-in-time wellness observation. Purely a record of what
    staff observed — never an automated interpretation or diagnosis. All
    vitals are optional (a visit might only note mood, or only weight)."""

    __tablename__ = "health_records"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    recorded_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    blood_pressure_systolic = db.Column(db.Integer, nullable=True)
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)
    temperature_celsius = db.Column(db.Numeric(4, 1), nullable=True)
    pulse_bpm = db.Column(db.Integer, nullable=True)
    weight_kg = db.Column(db.Numeric(5, 1), nullable=True)
    wellbeing = db.Column(db.String(10), nullable=True)
    mood = db.Column(db.String(60), nullable=True)
    physical_activity = db.Column(db.Text, nullable=True)
    observations = db.Column(db.Text, nullable=True)
    follow_up_required = db.Column(db.Boolean, default=False, nullable=False)
    follow_up_notes = db.Column(db.Text, nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "recorded_at": self.recorded_at.isoformat(),
            "blood_pressure_systolic": self.blood_pressure_systolic,
            "blood_pressure_diastolic": self.blood_pressure_diastolic,
            "temperature_celsius": float(self.temperature_celsius) if self.temperature_celsius is not None else None,
            "pulse_bpm": self.pulse_bpm,
            "weight_kg": float(self.weight_kg) if self.weight_kg is not None else None,
            "wellbeing": self.wellbeing,
            "mood": self.mood,
            "physical_activity": self.physical_activity,
            "observations": self.observations,
            "follow_up_required": self.follow_up_required,
            "follow_up_notes": self.follow_up_notes,
            "recorded_by": self.recorded_by.name,
            "created_at": self.created_at.isoformat(),
        }


MEDICATION_STATUSES = ("Active", "Completed", "Discontinued")
ADMINISTRATION_STATUSES = ("Given", "Missed", "Refused")


class Medication(db.Model):
    """A prescribed course. Individual doses are logged separately in
    MedicationAdministration — this row is the standing order, not a dose
    log. There is no automated push-reminder system yet (see docs/api);
    "reminders" today means the Active list itself."""

    __tablename__ = "medications"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    dosage = db.Column(db.String(100), nullable=True)
    instructions = db.Column(db.Text, nullable=True)
    schedule = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, default=lambda: utcnow().date(), nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Active")
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    created_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "name": self.name,
            "dosage": self.dosage,
            "instructions": self.instructions,
            "schedule": self.schedule,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class MedicationAdministration(db.Model):
    """One row per dose event — given, missed, or refused. This is the
    administration record the vision doc asks for; it's staff-logged, not
    device- or patient-reported."""

    __tablename__ = "medication_administrations"

    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey("medications.id"), nullable=False, index=True)
    administered_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Given")
    notes = db.Column(db.Text, nullable=True)
    administered_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    administered_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "medication_id": self.medication_id,
            "administered_at": self.administered_at.isoformat(),
            "status": self.status,
            "notes": self.notes,
            "administered_by": self.administered_by.name,
            "created_at": self.created_at.isoformat(),
        }


class TeamMember(db.Model):
    __tablename__ = "team_members"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(120), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "image": self.image,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
