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


DONATION_STATUSES = ("Paid", "Pending", "Received")
DONATION_FREQUENCIES = ("one-time", "monthly")
DONATION_TYPES = ("Cash", "Food", "Equipment")


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    # Cash (the original, public-facing shape) vs Food/Equipment (staff-
    # logged in-kind gifts — see app/donations/routes.py's
    # create_admin_donation). server_default backfills existing rows to
    # 'Cash' when this column was added by migration.
    donation_type = db.Column(db.String(20), nullable=False, default="Cash", server_default="Cash")
    donor_name = db.Column(db.String(120), nullable=False)
    # Nullable at the DB level (an in-person in-kind donor may not leave
    # contact info) but still required=True in DonationCreateSchema for
    # the public Cash flow — the column is looser than the public API.
    donor_email = db.Column(db.String(255), nullable=True)
    donor_phone = db.Column(db.String(40), nullable=True)
    # Required for Cash (a payment amount); for Food/Equipment this is an
    # optional estimated value, not a payment — same column, no separate
    # "estimated_value" field, since both mean "value of this gift."
    amount = db.Column(db.Numeric(10, 2), nullable=True)
    currency = db.Column(db.String(8), nullable=False, default="KES")
    frequency = db.Column(db.String(20), nullable=False, default="one-time")
    # Doubles as "purpose/category" for every donation type, not just Cash.
    campaign = db.Column(db.String(120), nullable=True)
    payment_method = db.Column(db.String(40), nullable=True)
    # Food/Equipment only: what was given, how much, in what unit.
    item_description = db.Column(db.Text, nullable=True)
    quantity = db.Column(db.Numeric(10, 2), nullable=True)
    unit = db.Column(db.String(30), nullable=True)
    # NOTE: no real payment gateway is integrated in this project. "status"
    # is a workflow label the org uses internally, never a verified payment
    # confirmation. It is always server-set on creation (never taken from
    # the public-facing create request) and can only be changed afterward
    # by an authenticated admin/staff edit. Cash defaults to "Paid";
    # Food/Equipment default to "Received" (see docs/api/donations.md).
    status = db.Column(db.String(20), nullable=False, default="Paid")
    txn_id = db.Column(db.String(60), unique=True, nullable=False)
    receipt_id = db.Column(db.String(60), unique=True, nullable=False)
    message = db.Column(db.Text, nullable=True)
    # Indexed for reports/routes.py's date-range/grouped donation queries.
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "donation_type": self.donation_type,
            "donor_name": self.donor_name,
            "donor_email": self.donor_email,
            "donor_phone": self.donor_phone,
            "amount": float(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "frequency": self.frequency,
            "campaign": self.campaign,
            "payment_method": self.payment_method,
            "item_description": self.item_description,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "unit": self.unit,
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


VOLUNTEER_STATUSES = ("Pending", "Verified", "Rejected")


class VolunteerProfile(db.Model):
    """Extra profile data for a User with role='volunteer'. Kept separate
    from User (the auth record) since not every field here belongs on
    every account, and self-registration only ever produces a bare User —
    this row is created alongside it (see auth/routes.py) with status
    Pending, then staff verify it here. Assignment history and hours are
    intentionally not stored here — they're derived from HomeVisit rows
    once that module exists, not duplicated."""

    __tablename__ = "volunteer_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    skills = db.Column(db.Text, nullable=True)
    availability = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.user.name,
            "email": self.user.email,
            "phone": self.phone,
            "skills": self.skills,
            "availability": self.availability,
            "bio": self.bio,
            "status": self.status,
            "reviewed_by": self.reviewed_by.name if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


HOME_VISIT_PRIORITIES = ("Low", "Medium", "High", "Urgent")
HOME_VISIT_STATUSES = ("Pending", "Assigned", "Scheduled", "In Progress", "Completed", "Cancelled")


class HomeVisit(db.Model):
    """A visit request for an elderly member who can't (or doesn't) come
    to the centre. assigned_to is a User — either staff/admin (a
    caregiver) or a volunteer with a Verified VolunteerProfile; that's
    checked in the route, not the DB, since it depends on a second table.
    No strict status state machine — admin/staff can set any status
    directly, same as every other module's PATCH. The assigned user
    (staff or a verified volunteer) can update their own visit's outcome
    fields (status/observations/support_provided/follow-up) but not
    reassign it or change the elderly member/priority/reason — see the
    two schemas in this module and the ownership check in routes.py."""

    __tablename__ = "home_visits"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Pending")
    reason = db.Column(db.Text, nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    observations = db.Column(db.Text, nullable=True)
    support_provided = db.Column(db.Text, nullable=True)
    follow_up_required = db.Column(db.Boolean, default=False, nullable=False)
    follow_up_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "requested_by": self.requested_by.name,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to": self.assigned_to.name if self.assigned_to else None,
            "priority": self.priority,
            "status": self.status,
            "reason": self.reason,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "observations": self.observations,
            "support_provided": self.support_provided,
            "follow_up_required": self.follow_up_required,
            "follow_up_notes": self.follow_up_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


MEAL_TYPES = ("Breakfast", "Lunch", "Snack", "Special")


class Meal(db.Model):
    """One meal event on one date — the plan/record, not a per-person log
    (see MealAttendance for that). Dietary requirements/restrictions are
    not duplicated here — they already live on ElderlyMember.allergies/
    dietary_requirements; the frontend surfaces those when marking
    attendance rather than storing a second copy that could drift."""

    __tablename__ = "meals"

    id = db.Column(db.Integer, primary_key=True)
    meal_date = db.Column(db.Date, default=lambda: utcnow().date(), nullable=False, index=True)
    meal_type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=True)
    planned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    planned_by = db.relationship("User")

    def to_dict(self, attendee_count=None):
        data = {
            "id": self.id,
            "meal_date": self.meal_date.isoformat(),
            "meal_type": self.meal_type,
            "description": self.description,
            "planned_by": self.planned_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if attendee_count is not None:
            data["attendee_count"] = attendee_count
        return data


class MealAttendance(db.Model):
    """Append-only, like the elderly Attendance/MedicationAdministration
    modules — no edit/delete. A row's existence means the member received
    (or was offered — see notes) this meal."""

    __tablename__ = "meal_attendance"
    __table_args__ = (db.UniqueConstraint("meal_id", "elderly_member_id", name="uq_meal_attendance_meal_member"),)

    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False, index=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "meal_id": self.meal_id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "notes": self.notes,
            "recorded_by": self.recorded_by.name,
            "created_at": self.created_at.isoformat(),
        }


INVENTORY_CATEGORIES = ("Food", "Medical", "Hygiene", "Equipment", "Other")
STOCK_MOVEMENT_TYPES = ("In", "Out")


class InventoryItem(db.Model):
    """current_stock is a running total maintained ONLY by StockMovement
    (see app/inventory/routes.py's _apply_movement) — no route ever lets a
    client set it directly, on create or edit. That's what keeps the
    movement ledger authoritative: the balance is always derivable from
    (and kept in sync with) the history, never a separately-editable
    number that could drift from it."""

    __tablename__ = "inventory_items"
    __table_args__ = (db.CheckConstraint("current_stock >= 0", name="ck_inventory_current_stock_non_negative"),)

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="Other")
    unit = db.Column(db.String(30), nullable=False)
    current_stock = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    minimum_stock = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "unit": self.unit,
            "current_stock": float(self.current_stock),
            "minimum_stock": float(self.minimum_stock),
            "low_stock": self.current_stock <= self.minimum_stock,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class StockMovement(db.Model):
    """Append-only ledger — no edit/delete endpoint, ever. A mistaken entry
    is corrected with a compensating movement (a real accounting
    practice), not by rewriting history. donation_id is an optional link
    when a stock-in came from a logged Donation (see docs/api/donations.md)
    for traceability; not every stock-in has one."""

    __tablename__ = "stock_movements"
    __table_args__ = (db.CheckConstraint("quantity > 0", name="ck_stock_movement_quantity_positive"),)

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    movement_type = db.Column(db.String(3), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    reason = db.Column(db.Text, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    donation_id = db.Column(db.Integer, db.ForeignKey("donations.id"), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Indexed for reports/routes.py's date-range/grouped movement queries.
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    item = db.relationship("InventoryItem")
    donation = db.relationship("Donation")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "movement_type": self.movement_type,
            "quantity": float(self.quantity),
            "reason": self.reason,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "donation_id": self.donation_id,
            "recorded_by": self.recorded_by.name,
            "created_at": self.created_at.isoformat(),
        }


ACTIVITY_TYPES = ("Exercise", "Walking", "Games", "Social", "Intergenerational", "Skills Training", "Educational", "Community Event", "Other")
ACTIVITY_STATUSES = ("Scheduled", "In Progress", "Completed", "Cancelled")
ACTIVITY_PARTICIPANT_STATUSES = ("Registered", "Attended", "No-show", "Cancelled")


class Activity(db.Model):
    """facilitator_id is validated the same way HomeVisit.assigned_to_id
    is (staff/admin or a Verified volunteer only — see
    app/activities/routes.py) since facilitating means direct contact
    with elderly members, same sensitivity as a home visit."""

    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    activity_type = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(150), nullable=True)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    facilitator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Scheduled")
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    facilitator = db.relationship("User", foreign_keys=[facilitator_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def to_dict(self, participant_count=None):
        data = {
            "id": self.id,
            "title": self.title,
            "activity_type": self.activity_type,
            "description": self.description,
            "location": self.location,
            "scheduled_at": self.scheduled_at.isoformat(),
            "facilitator_id": self.facilitator_id,
            "facilitator": self.facilitator.name if self.facilitator else None,
            "status": self.status,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if participant_count is not None:
            data["participant_count"] = participant_count
        return data


class ActivityParticipant(db.Model):
    """One row per elderly member per activity, carrying its own lifecycle
    (Registered -> Attended/No-show/Cancelled) rather than two separate
    registration and attendance tables — registering ahead of time and
    marking attendance afterward are the same relationship at different
    points in time, not two different facts."""

    __tablename__ = "activity_participants"
    __table_args__ = (db.UniqueConstraint("activity_id", "elderly_member_id", name="uq_activity_participant_activity_member"),)

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False, index=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="Registered")
    notes = db.Column(db.Text, nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "status": self.status,
            "notes": self.notes,
            "recorded_by": self.recorded_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


ASSISTANCE_TYPES = ("Hospital Accompaniment", "Transportation", "Food Assistance", "Companionship", "Home Support", "Other")
ASSISTANCE_PRIORITIES = ("Low", "Medium", "High", "Urgent")
ASSISTANCE_STATUSES = ("Requested", "Matching", "Assigned", "Accepted", "In Progress", "Completed", "Cancelled")


class AssistanceRequest(db.Model):
    """Request -> Matching -> Assignment -> Acceptance -> In Progress ->
    Completion, one status field, no enforced state machine (same
    principle as every other lifecycle module here). The one thing that
    IS enforced server-side: "Acceptance" is not just another status a
    PATCH can set — it's its own endpoint (POST .../accept) that only the
    assigned user can call, on their own request, moving Assigned ->
    Accepted. See app/assistance/routes.py.

    assigned_to_id follows the same rule as HomeVisit.assigned_to_id:
    staff/admin, or a volunteer only once Verified. home_visit_id is an
    optional link when a request turns into (or came from) a home visit —
    traceability, not a hard coupling, same pattern as
    StockMovement.donation_id."""

    __tablename__ = "assistance_requests"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    home_visit_id = db.Column(db.Integer, db.ForeignKey("home_visits.id"), nullable=True)
    request_type = db.Column(db.String(30), nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Requested")
    description = db.Column(db.Text, nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    outcome_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    home_visit = db.relationship("HomeVisit")

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "requested_by": self.requested_by.name,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to": self.assigned_to.name if self.assigned_to else None,
            "home_visit_id": self.home_visit_id,
            "request_type": self.request_type,
            "priority": self.priority,
            "status": self.status,
            "description": self.description,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "outcome_notes": self.outcome_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


INCIDENT_TYPES = ("Fall", "Injury", "Medical Concern", "Accident", "Safeguarding Concern", "Other")
INCIDENT_STATUSES = ("Open", "Under Review", "Resolved", "Closed")


class Incident(db.Model):
    """No DELETE endpoint, ever — a safeguarding/incident record is
    treated as a permanent record (real safeguarding practice: retain,
    don't erase), same append-only principle as the stock/administration
    ledgers, just applied to the whole record rather than a sub-log.
    Access is admin/staff only, no volunteer visibility at all — matching
    the brief's own role breakdown, where only Caregiver/Staff (not
    Volunteer) has "create incident reports" as a listed capability."""

    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    incident_type = db.Column(db.String(30), nullable=False)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    location = db.Column(db.String(150), nullable=True)
    description = db.Column(db.Text, nullable=False)
    immediate_action_taken = db.Column(db.Text, nullable=True)
    emergency_contact_notified = db.Column(db.Boolean, default=False, nullable=False)
    emergency_contact_notified_at = db.Column(db.DateTime(timezone=True), nullable=True)
    follow_up_required = db.Column(db.Boolean, default=False, nullable=False)
    follow_up_notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Open")
    resolution_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    reported_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "reported_by": self.reported_by.name,
            "incident_type": self.incident_type,
            "occurred_at": self.occurred_at.isoformat(),
            "location": self.location,
            "description": self.description,
            "immediate_action_taken": self.immediate_action_taken,
            "emergency_contact_notified": self.emergency_contact_notified,
            "emergency_contact_notified_at": self.emergency_contact_notified_at.isoformat() if self.emergency_contact_notified_at else None,
            "follow_up_required": self.follow_up_required,
            "follow_up_notes": self.follow_up_notes,
            "status": self.status,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


NOTIFICATION_TYPES = (
    "Medication Reminder", "Health Follow-up", "Home Visit Assignment", "Home Visit Reminder",
    "Assistance Request Assignment", "Low Inventory Alert", "Upcoming Activity",
    "Incident Follow-up", "Volunteer Verified", "System Notification",
)


class Notification(db.Model):
    """One row per (event, recipient) — not a separate NotificationRecipient
    join table. Every type here is inherently single-recipient in this
    system (an assignment, a personal alert); a rare broadcast (e.g. low
    stock to every admin) just costs a handful of duplicate rows, which is
    cheap at this system's scale and far simpler than a fan-out join table
    this system's actual usage never needs.

    related_resource_id is deliberately NOT a real foreign key: it's a
    polymorphic pointer (a notification can reference a home visit, an
    assistance request, an inventory item, ...) and a single SQL FK can
    only target one table. The alternative — one nullable FK column per
    possible target — is worse bloat for a field whose only job is "let
    the user navigate to what this is about." If the target is later
    deleted the notification becomes a dead link, a minor UX gap, not a
    data-integrity problem like every other FK in this system."""

    __tablename__ = "notifications"
    __table_args__ = (db.Index("ix_notifications_recipient_read", "recipient_id", "is_read"),)

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    notification_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    related_resource_type = db.Column(db.String(30), nullable=True)
    related_resource_id = db.Column(db.Integer, nullable=True)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    recipient = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "notification_type": self.notification_type,
            "title": self.title,
            "message": self.message,
            "related_resource_type": self.related_resource_type,
            "related_resource_id": self.related_resource_id,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "created_at": self.created_at.isoformat(),
        }


class InboxMessage(db.Model):
    """A public contact-form submission. Unlike Notification, this is a
    shared team mailbox, not identity-scoped: any admin/staff can view,
    mark, or delete any message, and the sender is a public visitor, not
    a User row — there is no recipient_id here at all."""

    __tablename__ = "inbox_messages"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "subject": self.subject,
            "message": self.message,
            "is_read": self.is_read,
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
