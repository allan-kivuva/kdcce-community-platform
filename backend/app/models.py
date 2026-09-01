import json
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db

ROLES = ("admin", "staff", "volunteer", "family")


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

    # --- Phase 7: administration & security ---------------------------
    active = db.Column(db.Boolean, nullable=False, default=True)
    last_login_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Soft delete for users only (see Phase 7 report for why this wasn't
    # extended to every table) — a deleted account is excluded from
    # default listings and cannot authenticate, but every row it created
    # or was assigned to stays intact and attributable.
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # TOTP secret is base32, written once at setup and read only by
    # totp_service — never included in any to_dict() output, anywhere,
    # after the one-time setup response that hands it to the user.
    totp_secret = db.Column(db.String(64), nullable=True)
    totp_enabled = db.Column(db.Boolean, nullable=False, default=False)
    totp_confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)

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
            "active": self.active,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "two_factor_enabled": self.totp_enabled,
            "created_at": self.created_at.isoformat(),
        }


DONOR_TYPES = ("Individual", "Organization", "Anonymous")


class Donor(db.Model):
    """A real donor identity, introduced in Phase 6 alongside the
    donor_name/donor_email/donor_phone fields Donation already had —
    those free-text fields are kept exactly as they were (backward
    compatibility for every existing row and every existing report/
    export that reads them) and Donor is additive: Donation.donor_id is
    a nullable pointer to one of these, populated where a match is
    confident, left null otherwise. See donors/service.py for the
    matching rules (both the migration backfill and new-donation
    auto-linking use the same normalized-email logic)."""

    __tablename__ = "donors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(40), nullable=True)
    organization = db.Column(db.String(150), nullable=True)
    donor_type = db.Column(db.String(20), nullable=False, default="Individual")
    notes = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    def to_dict(self, lifetime_amount=None, donation_count=None, most_recent_donation_at=None, campaigns_supported=None):
        data = {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "organization": self.organization,
            "donor_type": self.donor_type,
            "notes": self.notes,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if lifetime_amount is not None:
            data["lifetime_amount"] = float(lifetime_amount)
        if donation_count is not None:
            data["donation_count"] = donation_count
        if most_recent_donation_at is not None:
            data["most_recent_donation_at"] = most_recent_donation_at.isoformat() if most_recent_donation_at else None
        if campaigns_supported is not None:
            data["campaigns_supported"] = campaigns_supported
        return data


CAMPAIGN_STATUSES = ("Draft", "Active", "Paused", "Completed", "Archived")
# Statuses that represent real, counted money/goods — same "Paid or
# Received, never Pending" rule campaign progress and reports both use.
# Matches Donation.status's own documented semantics (see below): there
# is no real payment gateway, so "Paid"/"Received" are staff-confirmed
# workflow labels, not verified transactions — but they're still the
# right line between "counts" and "doesn't count yet."
DONATION_COUNTED_STATUSES = ("Paid", "Received")


class Campaign(db.Model):
    """A first-class fundraising campaign — Donation.campaign (free text)
    predates this and is left completely intact; Donation.campaign_id is
    an additive nullable pointer to one of these. A campaign may
    optionally belong to a Program (Phase 5), letting "raise money for
    the Feeding Program" be represented without Program itself carrying
    any fundraising fields of its own."""

    __tablename__ = "campaigns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    goal_amount = db.Column(db.Numeric(12, 2), nullable=False)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Draft")
    public_visible = db.Column(db.Boolean, default=False, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    program = db.relationship("Program")
    created_by = db.relationship("User")

    def to_dict(self, progress=None):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "goal_amount": float(self.goal_amount),
            "program_id": self.program_id,
            "program_name": self.program.name if self.program else None,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "public_visible": self.public_visible,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if progress is not None:
            data["progress"] = progress
        return data

    def public_dict(self, progress=None):
        """Deliberately a short, separate allowlist — never the general
        to_dict() — for the public campaign page. Excludes created_by,
        internal timestamps, and anything not meant to leave this
        endpoint even if to_dict() grows new internal fields later."""
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "goal_amount": float(self.goal_amount),
            "program_name": self.program.name if self.program else None,
            "status": self.status,
        }
        if progress is not None:
            data["progress"] = {k: progress[k] for k in ("raised_amount", "remaining_amount", "percent_achieved", "donation_count") if k in progress}
        return data


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
    # Kept exactly as-is (Phase 6); campaign_id below is the new,
    # optional, structured pointer — this free-text field is never
    # removed or auto-overwritten.
    campaign = db.Column(db.String(120), nullable=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True, index=True)
    donor_id = db.Column(db.Integer, db.ForeignKey("donors.id"), nullable=True, index=True)
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

    # Named campaign_obj/donor_ref, not campaign/donor — this model
    # already has a `campaign` free-text column, and "donor" reads
    # ambiguously right next to donor_name/donor_email/donor_phone.
    campaign_obj = db.relationship("Campaign")
    donor_ref = db.relationship("Donor")

    def to_dict(self):
        return {
            "id": self.id,
            "donation_type": self.donation_type,
            "donor_name": self.donor_name,
            "donor_email": self.donor_email,
            "donor_phone": self.donor_phone,
            "donor_id": self.donor_id,
            "amount": float(self.amount) if self.amount is not None else None,
            "currency": self.currency,
            "frequency": self.frequency,
            "campaign": self.campaign,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign_obj.name if self.campaign_obj else None,
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
    # Phase 8: optional, admin-triggered geocoding of `location` — never
    # populated automatically on create/update, only via the explicit
    # POST .../geocode action (see geocoding/routes.py). geocode_source
    # records which provider produced it ("offline" for this app's
    # built-in deterministic placeholder, see geocoding/service.py); a
    # real paid provider can be swapped in later without a schema change.
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    geocoded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    geocode_source = db.Column(db.String(30), nullable=True)
    geocode_accuracy = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    opa = db.relationship("OPA")

    def to_dict(self, include_coordinates=False):
        data = {
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
            "geocoded_at": self.geocoded_at.isoformat() if self.geocoded_at else None,
            "geocode_source": self.geocode_source,
            "geocode_accuracy": self.geocode_accuracy,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        # Exact coordinates are sensitive — every existing admin caller of
        # this to_dict() (elderly/routes.py) keeps getting the exact same
        # payload as before by default; only callers that explicitly ask
        # (the map endpoint) get latitude/longitude included at all.
        if include_coordinates:
            data["latitude"] = self.latitude
            data["longitude"] = self.longitude
        return data


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
    """Extra profile data for a User with role='volunteer' — and, since it
    already carries status/reviewed_by/reviewed_at, this row IS the
    volunteer application, not a separate thing from it. There's
    deliberately no distinct VolunteerApplication model: that would just
    duplicate the status/reviewer/timestamp bookkeeping already here.
    created_at doubles as "submitted_at" — the row is created alongside
    the User at registration (see auth/routes.py) with status Pending,
    then staff verify or reject it here. Assignment history and hours are
    intentionally not stored here — they're derived from HomeVisit rows,
    not duplicated."""

    __tablename__ = "volunteer_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    phone = db.Column(db.String(40), nullable=True)
    skills = db.Column(db.Text, nullable=True)
    # Free-text ("Weekday mornings"). Kept as-is, unenforced anywhere — a
    # human-readable summary the volunteer writes for their own profile.
    # VolunteerAvailability/VolunteerUnavailability below add STRUCTURED
    # availability alongside this, for anything that needs to actually
    # query/filter by day or time; this column isn't replaced or migrated
    # into that shape, since the two serve different purposes (a free-form
    # note vs. queryable data) and a volunteer may keep using either, both,
    # or neither.
    availability = db.Column(db.Text, nullable=True)
    areas_of_interest = db.Column(db.Text, nullable=True)
    experience = db.Column(db.Text, nullable=True)
    motivation = db.Column(db.Text, nullable=True)
    bio = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    rejection_reason = db.Column(db.Text, nullable=True)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Phase 8: optional, volunteer-provided coordinates (never derived
    # from their address automatically — there's no street-address field
    # on this model to geocode from) used only as a distance input to
    # smart matching (matching/service.py). Null for any volunteer who
    # hasn't set one; matching treats that as "no distance signal", not
    # as a scoring penalty.
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
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
            "areas_of_interest": self.areas_of_interest,
            "experience": self.experience,
            "motivation": self.motivation,
            "bio": self.bio,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "reviewed_by": self.reviewed_by.name if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


DAYS_OF_WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


class VolunteerAvailability(db.Model):
    """A recurring weekly window a volunteer has offered — e.g. "Mondays
    09:00-12:00". A volunteer has zero or more of these (one row per
    window, not one row per volunteer). Purely informational for admin/
    staff to consult when assigning work: nothing here validates or
    blocks assignment creation against it — that's a future
    smart-matching concern (see the architecture roadmap), not this one."""

    __tablename__ = "volunteer_availability"

    id = db.Column(db.Integer, primary_key=True)
    volunteer_profile_id = db.Column(db.Integer, db.ForeignKey("volunteer_profiles.id"), nullable=False, index=True)
    day_of_week = db.Column(db.String(10), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    volunteer_profile = db.relationship("VolunteerProfile")

    def to_dict(self):
        return {
            "id": self.id,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time.strftime("%H:%M"),
            "end_time": self.end_time.strftime("%H:%M"),
        }


class VolunteerUnavailability(db.Model):
    """A date range a volunteer has flagged as unavailable regardless of
    their usual weekly pattern above — e.g. a planned trip. Same
    informational-only scope as VolunteerAvailability."""

    __tablename__ = "volunteer_unavailability"

    id = db.Column(db.Integer, primary_key=True)
    volunteer_profile_id = db.Column(db.Integer, db.ForeignKey("volunteer_profiles.id"), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    volunteer_profile = db.relationship("VolunteerProfile")

    def to_dict(self):
        return {
            "id": self.id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "reason": self.reason,
        }


RECURRING_FREQUENCIES = ("weekly", "biweekly", "monthly")
RECURRING_SERIES_STATUSES = ("Active", "Paused", "Cancelled")


class RecurringVisitSeries(db.Model):
    """A recurring home-visit schedule. This does NOT replace or wrap the
    home-visit workflow — it materializes real HomeVisit rows (see
    recurring_visits/service.py's generate_occurrences), and every one of
    those is a normal HomeVisit, assignable/acceptable/completable through
    the exact same existing endpoints as a one-off visit, just linked back
    here via HomeVisit.recurring_series_id for traceability (same
    optional-link pattern as AssistanceRequest.home_visit_id).

    No background scheduler/job queue: occurrences are generated (a) up
    front through a horizon when the series is created, and (b) topped up
    by the `flask generate-recurring-visits` CLI command, meant to be run
    from a plain OS cron — matching this app's existing seed-admin/
    seed-demo CLI-command convention, not a new kind of infrastructure.

    occurrences_generated is the sole bookkeeping needed to resume
    generation without gaps or duplicates: occurrence N's calendar date is
    always deterministically computed from (start_date, frequency, N) —
    see service.py's occurrence_date() — so this counter alone says
    exactly how many have been created so far; generation always resumes
    at N = occurrences_generated and never revisits an earlier N."""

    __tablename__ = "recurring_visit_series"

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    frequency = db.Column(db.String(10), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    scheduled_time = db.Column(db.Time, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    occurrence_count = db.Column(db.Integer, nullable=True)
    occurrences_generated = db.Column(db.Integer, nullable=False, default=0)
    status = db.Column(db.String(10), nullable=False, default="Active")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])

    def to_dict(self, visit_count=None):
        data = {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to": self.assigned_to.name if self.assigned_to else None,
            "requested_by": self.requested_by.name,
            "reason": self.reason,
            "priority": self.priority,
            "frequency": self.frequency,
            "start_date": self.start_date.isoformat(),
            "scheduled_time": self.scheduled_time.strftime("%H:%M"),
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "occurrence_count": self.occurrence_count,
            "occurrences_generated": self.occurrences_generated,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if visit_count is not None:
            data["visit_count"] = visit_count
        return data


HOME_VISIT_PRIORITIES = ("Low", "Medium", "High", "Urgent")
# "Accepted"/"Started" added to give the volunteer field-work flow
# (Assigned -> Accepted -> Started -> In Progress -> Completed) the same
# vocabulary AssistanceRequest already partly had — extending the existing
# set, not a parallel status system. No strict state machine still applies:
# admin/staff can set any status directly, same as every other module.
HOME_VISIT_STATUSES = ("Pending", "Assigned", "Accepted", "Scheduled", "Started", "In Progress", "Completed", "Cancelled")


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
    # Set only on a visit generated by RecurringVisitSeries — null for a
    # normal one-off visit. Optional traceability link, same pattern as
    # AssistanceRequest.home_visit_id; a generated visit is otherwise a
    # completely ordinary HomeVisit row, not a distinct kind of record.
    recurring_series_id = db.Column(db.Integer, db.ForeignKey("recurring_visit_series.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    status = db.Column(db.String(20), nullable=False, default="Pending")
    reason = db.Column(db.Text, nullable=False)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    # Server-set the instant status first becomes "Started" (see routes.py) —
    # never accepted from the client, same principle as completed_at.
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    observations = db.Column(db.Text, nullable=True)
    support_provided = db.Column(db.Text, nullable=True)
    follow_up_required = db.Column(db.Boolean, default=False, nullable=False)
    follow_up_notes = db.Column(db.Text, nullable=True)
    # Admin/staff-only — settable only via the staff full-edit path, never
    # the assignee's own restricted PATCH, and never returned to a
    # volunteer viewing their own assigned visit (see to_dict's
    # include_private and the route's role check). For something staff
    # need on record about a visit that the assigned volunteer themselves
    # shouldn't see — distinct from observations/support_provided, which
    # the volunteer writes as part of their own completion report and
    # can always see back.
    staff_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    recurring_series = db.relationship("RecurringVisitSeries")

    def to_dict(self, include_private=False):
        data = {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "requested_by": self.requested_by.name,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to": self.assigned_to.name if self.assigned_to else None,
            "recurring_series_id": self.recurring_series_id,
            "priority": self.priority,
            "status": self.status,
            "reason": self.reason,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "observations": self.observations,
            "support_provided": self.support_provided,
            "follow_up_required": self.follow_up_required,
            "follow_up_notes": self.follow_up_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_private:
            data["staff_notes"] = self.staff_notes
        return data


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
    # Phase 8: optional link to a Program (e.g. "Feeding Program") for
    # reporting/traceability — additive, same optional-grouping pattern
    # Activity.program_id already uses; a Meal has always been valid
    # standalone and stays that way.
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True, index=True)
    planned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    planned_by = db.relationship("User")
    program = db.relationship("Program")

    def to_dict(self, attendee_count=None):
        data = {
            "id": self.id,
            "meal_date": self.meal_date.isoformat(),
            "meal_type": self.meal_type,
            "description": self.description,
            "program_id": self.program_id,
            "program_name": self.program.name if self.program else None,
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
    meal = db.relationship("Meal")

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

PROGRAM_STATUSES = ("Draft", "Active", "Paused", "Completed", "Archived")


class Program(db.Model):
    """An ongoing initiative (Feeding Program, Health & Wellness,
    Companionship, ...) that Activities can optionally be grouped under.
    Deliberately thin — a Program organizes Activities over time; it does
    not duplicate anything an Activity already tracks (no its own
    schedule/location-per-instance, no its own participant list). All of
    that stays on Activity; Program is the umbrella."""

    __tablename__ = "programs"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=True)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(60), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Draft")
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    coordinator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    target_population = db.Column(db.String(150), nullable=True)
    goals = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    coordinator = db.relationship("User")

    def to_dict(self, activity_count=None):
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "category": self.category,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "coordinator_id": self.coordinator_id,
            "coordinator": self.coordinator.name if self.coordinator else None,
            "location": self.location,
            "target_population": self.target_population,
            "goals": self.goals,
            "image_url": self.image_url,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if activity_count is not None:
            data["activity_count"] = activity_count
        return data


class Activity(db.Model):
    """facilitator_id is validated the same way HomeVisit.assigned_to_id
    is (staff/admin or a Verified volunteer only — see
    app/activities/routes.py) since facilitating means direct contact
    with elderly members, same sensitivity as a home visit.

    program_id is nullable and additive — an Activity has always been
    valid standalone, and stays that way; grouping it under a Program is
    optional, never required. capacity/registration_open/
    registration_deadline govern the volunteer self-RSVP flow (see
    ActivityVolunteer below) — they say nothing about elderly-member
    participation, which stays staff-managed via ActivityParticipant
    exactly as before."""

    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    activity_type = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(150), nullable=True)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    facilitator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Scheduled")
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True, index=True)
    capacity = db.Column(db.Integer, nullable=True)
    registration_open = db.Column(db.Boolean, default=True, nullable=False)
    registration_deadline = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    facilitator = db.relationship("User", foreign_keys=[facilitator_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    program = db.relationship("Program")

    def to_dict(self, participant_count=None, confirmed_volunteer_count=None, waitlist_count=None):
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
            "program_id": self.program_id,
            "program_name": self.program.name if self.program else None,
            "capacity": self.capacity,
            "registration_open": self.registration_open,
            "registration_deadline": self.registration_deadline.isoformat() if self.registration_deadline else None,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if participant_count is not None:
            data["participant_count"] = participant_count
        if confirmed_volunteer_count is not None:
            data["confirmed_volunteer_count"] = confirmed_volunteer_count
            data["spots_remaining"] = None if self.capacity is None else max(self.capacity - confirmed_volunteer_count, 0)
        if waitlist_count is not None:
            data["waitlist_count"] = waitlist_count
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
    activity = db.relationship("Activity")

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


ACTIVITY_VOLUNTEER_ROLES = ("Facilitator", "Support", "Registration", "Logistics", "General Volunteer")
ACTIVITY_VOLUNTEER_STATUSES = ("Assigned", "Confirmed", "Waitlisted", "Declined", "Cancelled", "Attended", "No Show")
# Statuses that occupy a capacity slot — Waitlisted/Declined/Cancelled
# never do; Attended still counts (they showed up, the slot was theirs).
ACTIVITY_VOLUNTEER_CONFIRMED_STATUSES = ("Assigned", "Confirmed", "Attended")


class ActivityVolunteer(db.Model):
    """A volunteer's relationship to one Activity — covers BOTH staff-
    assigned staffing (a specific role like Facilitator/Registration) and
    a volunteer's own self-service RSVP (role defaults to "General
    Volunteer") in one table, not two. They're the same underlying fact
    ("this volunteer is involved with this event") at different points
    of origin: assigned_by_id is set when staff created the row, and
    left null for a self-RSVP — that one column is what "My Assignments"
    vs "My RSVPs" splits on client-side, rather than needing a separate
    model or a redundant boolean.

    Same "one row per volunteer per activity, own status lifecycle"
    shape as ActivityParticipant, deliberately — registering ahead of
    time and checking in/out afterward are the same relationship at
    different points in time, not different facts.

    No separate Waitlist model: Waitlisted is just another status here,
    promoted (see activities/service.py) by created_at order — the
    simplest reliable ordering, no separate position column to keep in
    sync."""

    __tablename__ = "activity_volunteers"
    __table_args__ = (db.UniqueConstraint("activity_id", "volunteer_id", name="uq_activity_volunteer"),)

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(db.Integer, db.ForeignKey("activities.id"), nullable=False, index=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(30), nullable=False, default="General Volunteer")
    status = db.Column(db.String(20), nullable=False, default="Assigned")
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    assigned_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    confirmed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    checked_in_at = db.Column(db.DateTime(timezone=True), nullable=True)
    checked_out_at = db.Column(db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    activity = db.relationship("Activity")
    volunteer = db.relationship("User", foreign_keys=[volunteer_id])
    assigned_by = db.relationship("User", foreign_keys=[assigned_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "volunteer_id": self.volunteer_id,
            "volunteer_name": self.volunteer.name,
            "role": self.role,
            "status": self.status,
            "is_self_rsvp": self.assigned_by_id is None,
            "assigned_by": self.assigned_by.name if self.assigned_by else None,
            "assigned_at": self.assigned_at.isoformat(),
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
            "checked_in_at": self.checked_in_at.isoformat() if self.checked_in_at else None,
            "checked_out_at": self.checked_out_at.isoformat() if self.checked_out_at else None,
            "updated_at": self.updated_at.isoformat(),
        }


ASSISTANCE_TYPES = ("Hospital Accompaniment", "Transportation", "Food Assistance", "Companionship", "Home Support", "Other")
ASSISTANCE_PRIORITIES = ("Low", "Medium", "High", "Urgent")
# "Started" added between Accepted and In Progress — same field-work
# lifecycle extension as HOME_VISIT_STATUSES above.
ASSISTANCE_STATUSES = ("Requested", "Matching", "Assigned", "Accepted", "Started", "In Progress", "Completed", "Cancelled")


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
    # Server-set the instant status first becomes "Started" — never
    # accepted from the client, same principle as completed_at.
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    outcome_notes = db.Column(db.Text, nullable=True)
    follow_up_required = db.Column(db.Boolean, default=False, nullable=False)
    follow_up_notes = db.Column(db.Text, nullable=True)
    # Same admin/staff-only, never-volunteer-visible field as
    # HomeVisit.staff_notes — see that column's docstring.
    staff_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    requested_by = db.relationship("User", foreign_keys=[requested_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    home_visit = db.relationship("HomeVisit")

    def to_dict(self, include_private=False):
        data = {
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
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "outcome_notes": self.outcome_notes,
            "follow_up_required": self.follow_up_required,
            "follow_up_notes": self.follow_up_notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_private:
            data["staff_notes"] = self.staff_notes
        return data


INCIDENT_TYPES = (
    "Fall", "Injury", "Medical Concern", "Accident", "Safeguarding Concern", "Other",
    # Added for volunteer-submitted concern reports (see routes.py) — extends
    # the existing set rather than a parallel category list.
    "Safety Concern", "Welfare Concern", "Emergency", "Missing Person",
)
INCIDENT_STATUSES = ("Open", "Under Review", "Resolved", "Closed")
INCIDENT_SEVERITIES = ("Low", "Medium", "High", "Critical")


class Incident(db.Model):
    """No DELETE endpoint, ever — a safeguarding/incident record is
    treated as a permanent record (real safeguarding practice: retain,
    don't erase), same append-only principle as the stock/administration
    ledgers, just applied to the whole record rather than a sub-log.
    Access is admin/staff only, no volunteer visibility at all — matching
    the brief's own role breakdown, where only Caregiver/Staff (not
    Volunteer) has "create incident reports" as a listed capability.

    severity defaults to Medium (not nullable) — every incident needs a
    triage level, unlike the optional fields below it. A Critical severity
    fires a notification to every admin/staff on creation (see routes.py)
    via the existing notify() chokepoint — no second notification path."""

    __tablename__ = "incidents"

    id = db.Column(db.Integer, primary_key=True)
    # Nullable: a volunteer's "Report a Concern" (see incidents/routes.py)
    # may not be about a specific member — admin/staff incident reports
    # still always name one (enforced in IncidentSchema, not here).
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=True, index=True)
    reported_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Who's handling this concern — admin/staff only (never a volunteer:
    # incidents stay entirely invisible to volunteers, so assigning one to
    # a volunteer would hand them a record they still couldn't see; see
    # incidents/routes.py's _staff_assignee_or_400).
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    incident_type = db.Column(db.String(30), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default="Medium")
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
    reported_by = db.relationship("User", foreign_keys=[reported_by_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name if self.elderly_member else None,
            "elderly_member_code": self.elderly_member.member_id if self.elderly_member else None,
            "reported_by": self.reported_by.name,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to": self.assigned_to.name if self.assigned_to else None,
            "incident_type": self.incident_type,
            "severity": self.severity,
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


FOLLOW_UP_SOURCE_TYPES = ("health_record", "home_visit", "assistance_request", "incident")
FOLLOW_UP_PRIORITIES = ("Low", "Medium", "High", "Urgent")
FOLLOW_UP_STATUSES = ("Pending", "In Progress", "Completed")


class FollowUp(db.Model):
    """Turns the follow_up_required flag already on HealthRecord,
    HomeVisit, AssistanceRequest, and Incident into an actual, assignable,
    trackable task — those 4 models already had the flag; nothing acted
    on it. source_type/source_id is the same polymorphic pointer already
    established by Notification.related_resource_id and
    AssignmentAttachment/AssignmentMessage — a single FK can't target 4
    different tables, and a nullable FK column per possible source is
    worse bloat for a field whose only job is "what triggered this."
    elderly_member_id IS a real FK, unlike the source pointer — every
    follow-up is about one specific person regardless of which module it
    came from, and that's what every list/filter/timeline view actually
    queries by.

    "Overdue" is deliberately NOT a stored status — it's a computed
    condition (status != Completed and due_date < today), the same way
    this app derives rather than stores every other time-based view (e.g.
    low-stock is a live column comparison, not a stored flag)."""

    __tablename__ = "follow_ups"
    __table_args__ = (
        db.Index("ix_follow_ups_elderly_status", "elderly_member_id", "status"),
        db.Index("ix_follow_ups_source", "source_type", "source_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    source_type = db.Column(db.String(20), nullable=False)
    source_id = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(10), nullable=False, default="Medium")
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    notes = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def to_dict(self):
        today = utcnow().date()
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "elderly_member_code": self.elderly_member.member_id,
            "source_type": self.source_type,
            "source_id": self.source_id,
            "reason": self.reason,
            "priority": self.priority,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to": self.assigned_to.name if self.assigned_to else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "is_overdue": self.status != "Completed" and self.due_date is not None and self.due_date < today,
            "notes": self.notes,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


NOTIFICATION_TYPES = (
    "Medication Reminder", "Health Follow-up", "Home Visit Assignment", "Home Visit Reminder",
    "Assistance Request Assignment", "Low Inventory Alert", "Upcoming Activity",
    "Incident Follow-up", "Volunteer Verified", "Volunteer Rejected", "Assignment Message",
    "Follow-up Assigned", "Follow-up Overdue", "Critical Incident", "Assignment Reviewed", "System Notification",
    "Achievement Awarded", "Document Verified", "Document Rejected",
    "Direct Message", "Broadcast Message", "Announcement", "Urgent Announcement",
    "Event Assigned", "Event RSVP Confirmed", "Event Waitlisted", "Event Waitlist Promoted", "Event Cancelled",
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


class RevokedToken(db.Model):
    """A denylist of logged-out JWTs, checked on every authenticated
    request via jwt.token_in_blocklist_loader (see app/auth/routes.py).
    Without this, there is no way to invalidate an access or refresh
    token before its natural expiry (1h / 30d) — logout would only ever
    be a client-side localStorage clear, and a copied/leaked token would
    stay valid regardless. Rows are never cleaned up here (no scheduler
    exists in this codebase yet, same constraint noted for notification
    reminders); a revoked row past its original token's expiry is simply
    inert, just unpruned storage."""

    __tablename__ = "revoked_tokens"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


ASSIGNMENT_TYPES = ("home_visit", "assistance_request")


class AssignmentAttachment(db.Model):
    """An optional photo attached to a HomeVisit or AssistanceRequest on
    completion. assignment_type + assignment_id is the same polymorphic
    pointer as Notification.related_resource_id, for the same reason: a
    single FK can't target two tables, and one nullable FK column per
    possible target is worse bloat than this. At most one row per
    (assignment_type, assignment_id) — "a photo," not "photos."

    The actual file lives on disk under instance/uploads/assignment_photos/
    (never under app/static/ — nothing serves that path publicly), named by
    storage_key, a server-generated uuid4, never the client's filename.
    original_filename is display-only metadata; it is never used to build
    a filesystem path. mime_type is what the server verified from the
    file's own bytes, not what the client's Content-Type header claimed."""

    __tablename__ = "assignment_attachments"
    __table_args__ = (db.UniqueConstraint("assignment_type", "assignment_id", name="uq_assignment_attachment"),)

    id = db.Column(db.Integer, primary_key=True)
    assignment_type = db.Column(db.String(20), nullable=False)
    assignment_id = db.Column(db.Integer, nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    storage_key = db.Column(db.String(64), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    uploaded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "file_size": self.file_size,
            "uploaded_by": self.uploaded_by.name,
            "created_at": self.created_at.isoformat(),
        }


class AssignmentMessage(db.Model):
    """A private message on a HomeVisit or AssistanceRequest's own
    conversation thread — the volunteer assigned to it and admin/staff
    only, never a public/general chat. Same polymorphic
    assignment_type/assignment_id pointer as AssignmentAttachment, for the
    same reason."""

    __tablename__ = "assignment_messages"
    __table_args__ = (db.Index("ix_assignment_messages_assignment", "assignment_type", "assignment_id"),)

    id = db.Column(db.Integer, primary_key=True)
    assignment_type = db.Column(db.String(20), nullable=False)
    assignment_id = db.Column(db.Integer, nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    sender = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.name,
            "body": self.body,
            "created_at": self.created_at.isoformat(),
        }


class AssignmentReview(db.Model):
    """Admin's review of a completed HomeVisit or AssistanceRequest — a
    1-5 star rating plus an optional comment on how the volunteer/staff
    member handled it. Same polymorphic assignment_type/assignment_id
    pointer as AssignmentAttachment/AssignmentMessage, for the same
    reason (one FK can't target two tables). At most one review per
    assignment — submitting again replaces it, same "create or replace"
    behavior as AssignmentAttachment's photo, not a review history.

    Deliberately admin-only to create (see roles_required("admin") in
    routes.py, not the usual ("admin", "staff") pair used everywhere
    else in this app) — reviewing/rating a volunteer's work is reserved
    to admin specifically. Only allowed once the assignment's own status
    is Completed; reviewing incomplete work doesn't make sense."""

    __tablename__ = "assignment_reviews"
    __table_args__ = (db.UniqueConstraint("assignment_type", "assignment_id", name="uq_assignment_review"),)

    id = db.Column(db.Integer, primary_key=True)
    assignment_type = db.Column(db.String(20), nullable=False)
    assignment_id = db.Column(db.Integer, nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    reviewed_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "rating": self.rating,
            "comment": self.comment,
            "reviewed_by": self.reviewed_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AssignmentChecklistItem(db.Model):
    """One row per checked/unchecked item on a HomeVisit or
    AssistanceRequest's fixed, type-specific checklist (see
    assignments/service.py's CHECKLIST_DEFINITIONS — the item set itself is
    defined in code, not user-editable, so there's nothing to store beyond
    which fixed items are checked). Same polymorphic assignment_type/
    assignment_id pointer as AssignmentAttachment/Message/Review, for the
    same reason (one FK can't target two tables). A row only exists once an
    item has been toggled at least once — GET synthesizes the full,
    unchecked-by-default list by merging these rows over
    CHECKLIST_DEFINITIONS, so there's no need to pre-create rows for every
    item on every assignment up front."""

    __tablename__ = "assignment_checklist_items"
    __table_args__ = (db.UniqueConstraint("assignment_type", "assignment_id", "item_key", name="uq_assignment_checklist_item"),)

    id = db.Column(db.Integer, primary_key=True)
    assignment_type = db.Column(db.String(20), nullable=False)
    assignment_id = db.Column(db.Integer, nullable=False)
    item_key = db.Column(db.String(40), nullable=False)
    checked = db.Column(db.Boolean, default=False, nullable=False)
    checked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    checked_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    checked_by = db.relationship("User")

    def to_dict(self):
        return {
            "item_key": self.item_key,
            "checked": self.checked,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
            "checked_by": self.checked_by.name if self.checked_by else None,
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


# ============================================================
# Phase 3 — Volunteer Management & Engagement
# ============================================================
# All of the tables below anchor on volunteer_profile_id (not user_id
# directly) — same anchor as VolunteerAvailability/VolunteerUnavailability
# from Phase 2, for the same reason: these are all facts about the
# volunteer relationship specifically, not the bare User account.

VOLUNTEER_HOURS_CATEGORIES = ("Home Visit", "Assistance", "Activity", "Training", "Administrative", "Other")
VOLUNTEER_HOURS_STATUSES = ("Pending", "Approved", "Rejected")


class VolunteerHours(db.Model):
    """Manually-submitted service hours — a supplement to, not a
    replacement for, the automatic hours derived live from completed
    HomeVisit/AssistanceRequest started_at/completed_at pairs (see
    volunteer_hours/service.py). Only Approved rows count toward any
    total; Pending/Rejected never do, so a total can never be inflated by
    an unreviewed or declined claim. Minutes, not floating-point hours —
    the UI formats for display, this table never stores a fraction."""

    __tablename__ = "volunteer_hours"
    __table_args__ = (db.CheckConstraint("duration_minutes > 0", name="ck_volunteer_hours_duration_positive"),)

    id = db.Column(db.Integer, primary_key=True)
    volunteer_profile_id = db.Column(db.Integer, db.ForeignKey("volunteer_profiles.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="Other")
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    submitted_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    volunteer_profile = db.relationship("VolunteerProfile")
    approved_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "volunteer_profile_id": self.volunteer_profile_id,
            "date": self.date.isoformat(),
            "duration_minutes": self.duration_minutes,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "submitted_at": self.submitted_at.isoformat(),
            "approved_by": self.approved_by.name if self.approved_by else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


ACHIEVEMENT_CATEGORIES = ("Hours", "Visits", "Assistance", "Training", "Recognition")
# "manual" = never auto-awarded — only ever created via the recognition
# endpoint (Volunteer of the Month, Community Champion, ...). Every other
# type is a deterministic threshold the checker in achievements/service.py
# evaluates against real computed data — never an estimate or AI guess.
ACHIEVEMENT_THRESHOLD_TYPES = ("service_minutes", "completed_visits", "completed_assistance", "completed_assignments", "training_completed", "manual")


class Achievement(db.Model):
    """A badge DEFINITION — a reference/lookup table, like OPA, not a
    per-volunteer record (VolunteerAchievement below is that). Seeded once
    with a fixed starter set in this feature's own migration; no
    admin-facing create/edit API in this phase (deliberately not
    overbuilt — see the final report's deferred-items list)."""

    __tablename__ = "achievements"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(40), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(40), nullable=True)
    category = db.Column(db.String(20), nullable=False)
    threshold_type = db.Column(db.String(30), nullable=False)
    threshold_value = db.Column(db.Integer, nullable=True)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category,
            "threshold_type": self.threshold_type,
            "threshold_value": self.threshold_value,
            "active": self.active,
        }


class VolunteerAchievement(db.Model):
    """One earned badge. `source` distinguishes an automatic threshold
    award (see achievements/service.py's checker, awarded_by_id null)
    from a manual recognition award (awarded_by_id is the acting admin/
    staff user). A UniqueConstraint enforces "at most once per volunteer
    per achievement" for BOTH kinds — including recognition-type ones —
    same "create it once, don't duplicate" principle as
    ActivityParticipant/AssignmentReview elsewhere in this app. A
    genuinely repeat-worthy recognition (e.g. Volunteer of the Month
    again, a different month) is a real product question about whether
    that should be trackable per-period; deferred rather than guessed at
    (see the final report)."""

    __tablename__ = "volunteer_achievements"
    __table_args__ = (db.UniqueConstraint("volunteer_profile_id", "achievement_id", name="uq_volunteer_achievement"),)

    id = db.Column(db.Integer, primary_key=True)
    volunteer_profile_id = db.Column(db.Integer, db.ForeignKey("volunteer_profiles.id"), nullable=False, index=True)
    achievement_id = db.Column(db.Integer, db.ForeignKey("achievements.id"), nullable=False, index=True)
    awarded_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    awarded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    source = db.Column(db.String(20), nullable=False, default="automatic")
    notes = db.Column(db.Text, nullable=True)

    achievement = db.relationship("Achievement")
    awarded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "achievement": self.achievement.to_dict(),
            "awarded_at": self.awarded_at.isoformat(),
            "awarded_by": self.awarded_by.name if self.awarded_by else None,
            "source": self.source,
            "notes": self.notes,
        }


TRAINING_PROGRESS_STATUSES = ("Not Started", "In Progress", "Completed")


class TrainingCourse(db.Model):
    """A course is a title/description/resource link, not hosted content —
    "a simple title/description/resource link... is enough for the first
    implementation," so this deliberately has no lesson/module/quiz
    structure. `required` is informational (surfaced prominently in the
    UI); nothing server-side currently blocks or enforces it."""

    __tablename__ = "training_courses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(60), nullable=True)
    resource_url = db.Column(db.String(500), nullable=True)
    estimated_minutes = db.Column(db.Integer, nullable=True)
    required = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    created_by = db.relationship("User")

    def to_dict(self, completion_count=None):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "resource_url": self.resource_url,
            "estimated_minutes": self.estimated_minutes,
            "required": self.required,
            "active": self.active,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if completion_count is not None:
            data["completion_count"] = completion_count
        return data


class TrainingProgress(db.Model):
    """One row per (course, volunteer) — created on first interaction
    (Not Started never needs a stored row; a row only exists once a
    volunteer has actually started or completed something), same
    "synthesize the default, only store the exception" principle as
    AssignmentChecklistItem. completed_at is server-set the instant
    status first becomes Completed, never client-supplied."""

    __tablename__ = "training_progress"
    __table_args__ = (db.UniqueConstraint("course_id", "volunteer_profile_id", name="uq_training_progress"),)

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("training_courses.id"), nullable=False, index=True)
    volunteer_profile_id = db.Column(db.Integer, db.ForeignKey("volunteer_profiles.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="Not Started")
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    course = db.relationship("TrainingCourse")
    volunteer_profile = db.relationship("VolunteerProfile")

    def to_dict(self):
        return {
            "id": self.id,
            "course_id": self.course_id,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat(),
        }


DOCUMENT_TYPES = ("Identification", "Volunteer Agreement", "Certificate", "Training Certificate", "Other")
# "Expired" is deliberately NOT a stored status value here — see
# documents/service.py's expiry_state(): computed live from expiry_date at
# read time, same "derive, don't stow a flag that can go stale" principle
# as FollowUp.is_overdue/InventoryItem.low_stock. `status` below is only
# ever the admin verification workflow.
DOCUMENT_STATUSES = ("Pending", "Verified", "Rejected")


RESOURCE_VISIBILITIES = ("Admin", "Volunteers")


class Document(db.Model):
    """Generic, reusable file-attachment record — owner_type/owner_id is
    the same polymorphic pointer already used for Notification/
    AssignmentAttachment/FollowUp, so this can anchor to a volunteer today
    and a program/resource later without a schema change — exactly the
    reuse this pointer was built for. Phase 3 used only
    owner_type="volunteer" (pointing at a volunteer_profiles.id); Phase 5
    adds owner_type="program" (owner_id=programs.id), "activity"
    (owner_id=activities.id), and "general" (owner_id=uploaded_by_id, for
    a resource not tied to any specific program/activity) for the
    resource library, reusing this exact table and its storage mechanism
    rather than building a second file-storage system. `description` and
    `visibility` are additive, resource-only columns — a volunteer's own
    document leaves both null, same as `category`/`visibility` never
    applying to that flow. `document_type` doubles as a resource's
    category (e.g. "Program Guide", "Policy") — validated against a
    different vocabulary per upload context in the schema layer, not a
    second column, since it's the same "what kind of file is this"
    question either way. Reuses the exact storage approach as
    AssignmentAttachment (magic-byte sniffing, uuid4 storage key, never
    the client's filename/mime) — see documents/service.py — extended to
    also accept PDF, since agreements/certificates are usually PDFs, not
    photos."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    owner_type = db.Column(db.String(20), nullable=False, index=True)
    owner_id = db.Column(db.Integer, nullable=False, index=True)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    document_type = db.Column(db.String(30), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(20), nullable=True)
    storage_key = db.Column(db.String(64), unique=True, nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(50), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    issue_date = db.Column(db.Date, nullable=True)
    expiry_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])
    reviewed_by = db.relationship("User", foreign_keys=[reviewed_by_id])

    def to_dict(self):
        today = utcnow().date()
        expiry_state = None
        if self.expiry_date is not None:
            if self.expiry_date < today:
                expiry_state = "expired"
            elif (self.expiry_date - today).days <= 30:
                expiry_state = "expiring_soon"
            else:
                expiry_state = "valid"
        return {
            "id": self.id,
            "owner_type": self.owner_type,
            "owner_id": self.owner_id,
            "uploaded_by": self.uploaded_by.name,
            "document_type": self.document_type,
            "title": self.title,
            "description": self.description,
            "visibility": self.visibility,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "expiry_state": expiry_state,
            "status": self.status,
            "reviewed_by": self.reviewed_by.name if self.reviewed_by else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================
# Phase 4 — Communication: general direct messaging, broadcasts,
# and announcements. Assignment-scoped messaging (AssignmentMessage,
# above) is untouched — this is the general-purpose layer the
# architecture audit found missing: communication that doesn't
# depend on a HomeVisit/AssistanceRequest existing first.
# ============================================================

class Conversation(db.Model):
    """A direct, two-party conversation — always exactly one row per
    unordered pair of users (see messaging/service.py's find-or-create),
    never a group thread. user_one_id/user_two_id have no meaning beyond
    "the two participants"; `other_user()`/`read_at_for()` below hide
    that asymmetry from every caller so nothing has to know or care which
    slot a given user landed in.

    Read state is a single per-participant timestamp, not a per-message
    flag — a message is unread for a user iff it was sent after that
    user's own read_at and wasn't sent by them. That's the "thread-level
    read marker" this app's own message volume actually calls for,
    avoiding a row-per-message-per-participant table this scale never
    needs."""

    __tablename__ = "conversations"
    __table_args__ = (db.Index("ix_conversations_participants", "user_one_id", "user_two_id"),)

    id = db.Column(db.Integer, primary_key=True)
    user_one_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_two_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    # Phase 8: which elderly member a family account's conversation with
    # care staff is about — null for every ordinary (non-family)
    # conversation. Set once, at creation, from the authorized
    # FamilyMemberAccess the family account used to start it (see
    # family/routes.py) — never client-supplied on its own. A family
    # account with more than one linked member keeps one conversation
    # per staffer regardless of which member a later message concerns;
    # this only tags which member the thread was originally opened
    # about, a deliberate simplification over per-message tagging.
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_message_at = db.Column(db.DateTime(timezone=True), nullable=True)
    user_one_read_at = db.Column(db.DateTime(timezone=True), nullable=True)
    user_two_read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user_one = db.relationship("User", foreign_keys=[user_one_id])
    user_two = db.relationship("User", foreign_keys=[user_two_id])
    elderly_member = db.relationship("ElderlyMember")

    def is_participant(self, user_id):
        return user_id in (self.user_one_id, self.user_two_id)

    def other_user(self, user_id):
        return self.user_two if user_id == self.user_one_id else self.user_one

    def read_at_for(self, user_id):
        return self.user_one_read_at if user_id == self.user_one_id else self.user_two_read_at

    def set_read_at_for(self, user_id, value):
        if user_id == self.user_one_id:
            self.user_one_read_at = value
        else:
            self.user_two_read_at = value


class DirectMessage(db.Model):
    """One message in a Conversation. Same shape as AssignmentMessage
    (sender_id, body, created_at) — deliberately, this is the same
    convention applied to a conversation that isn't tied to an
    assignment."""

    __tablename__ = "direct_messages"
    __table_args__ = (db.Index("ix_direct_messages_conversation", "conversation_id", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id"), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    sender = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "sender_name": self.sender.name,
            "body": self.body,
            "created_at": self.created_at.isoformat(),
        }


ANNOUNCEMENT_PRIORITIES = ("Normal", "Important", "Urgent")
# "Family" added in Phase 8, alongside the new family role — see the
# "All" handling in announcements/service.py: family is deliberately
# excluded from "All" (which predates the family role and always meant
# "everyone on the operational side"), so an admin must explicitly pick
# "Family" to reach them. Otherwise every existing "All" announcement
# would silently start reaching family accounts the moment one exists.
COMMUNICATION_AUDIENCES = ("All", "Volunteers", "Verified Volunteers", "Staff", "Admin", "Family", "Selected")


class Announcement(db.Model):
    """Durable, audience-targeted content — shown on relevant dashboards
    while active, unlike a Notification (which is a one-shot per-user
    event that's dismissed and forgotten). audience_type drives who sees
    it; "Selected" additionally consults AnnouncementRecipient for the
    exact user list. publish_at/expires_at let staff schedule ahead or
    let something expire on its own — visibility is always derived at
    read time (see announcements/service.py), never a stored boolean
    that could drift out of sync with the clock."""

    __tablename__ = "announcements"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default="Normal")
    audience_type = db.Column(db.String(20), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    publish_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    created_by = db.relationship("User")
    recipients = db.relationship("AnnouncementRecipient", cascade="all, delete-orphan", backref="announcement")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "priority": self.priority,
            "audience_type": self.audience_type,
            "selected_user_ids": [r.user_id for r in self.recipients] if self.audience_type == "Selected" else None,
            "created_by": self.created_by.name,
            "publish_at": self.publish_at.isoformat() if self.publish_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "active": self.active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class AnnouncementRecipient(db.Model):
    """One row per targeted user when audience_type == "Selected" — only
    populated/consulted for that audience type, same "only used by the
    one mode that needs it" shape as VolunteerAchievement.notes."""

    __tablename__ = "announcement_recipients"
    __table_args__ = (db.UniqueConstraint("announcement_id", "user_id", name="uq_announcement_recipient"),)

    id = db.Column(db.Integer, primary_key=True)
    announcement_id = db.Column(db.Integer, db.ForeignKey("announcements.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class Broadcast(db.Model):
    """An audit record of one broadcast send — the durable "what was sent,
    to whom, by whom, when" history. Delivery itself is real Notification
    rows created via notify() for each resolved recipient (see
    broadcasts/service.py); this table does not duplicate that, it just
    remembers the send happened. client_token is an optional
    client-generated idempotency key: a retried submit with the same
    token returns the original broadcast instead of fanning out
    notifications a second time."""

    __tablename__ = "broadcasts"
    __table_args__ = (db.UniqueConstraint("client_token", name="uq_broadcast_client_token"),)

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    audience_type = db.Column(db.String(20), nullable=False)
    audience_detail = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    recipient_count = db.Column(db.Integer, nullable=False, default=0)
    client_token = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    sender = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender.name,
            "audience_type": self.audience_type,
            "audience_detail": [int(x) for x in self.audience_detail.split(",")] if self.audience_detail else None,
            "title": self.title,
            "message": self.message,
            "recipient_count": self.recipient_count,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================
# Phase 6 — Donations & Finance: Donor/Campaign live above, next to
# Donation. Expense/Budget/AuditLog live here, built around the Phase 5
# Program model and (for expense receipts) the Phase 3 Document model.
# ============================================================

EXPENSE_CATEGORIES = (
    "Food", "Medical", "Transport", "Utilities", "Program Supplies", "Events", "Maintenance", "Administration", "Other",
)
# "Recorded" is the only status staff can set directly; "Approved"/
# "Rejected" are admin-only sign-off actions (see expenses/routes.py) —
# same precedent as AssignmentReview being admin-only while everything
# else in that module is ("admin", "staff"). "Voided" reverses an
# already-recorded expense without deleting it (an audit trail, not a
# silent disappearance).
EXPENSE_STATUSES = ("Recorded", "Approved", "Rejected", "Voided")
# What counts as real, still-standing spend for budget/report totals.
EXPENSE_COUNTED_STATUSES = ("Recorded", "Approved")


class Expense(db.Model):
    """A recorded expenditure, optionally tied to a Program and/or
    Campaign. document_id optionally points at a Document (Phase 3's
    generalized file-attachment model, owner_type="expense") for a
    receipt or supporting file — reused exactly as designed, not a new
    upload system."""

    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(30), nullable=False)
    description = db.Column(db.Text, nullable=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True, index=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("campaigns.id"), nullable=True)
    expense_date = db.Column(db.Date, nullable=False, index=True)
    vendor_name = db.Column(db.String(150), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Recorded")
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    program = db.relationship("Program")
    campaign = db.relationship("Campaign")
    document = db.relationship("Document")
    recorded_by = db.relationship("User", foreign_keys=[recorded_by_id])
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "amount": float(self.amount),
            "category": self.category,
            "description": self.description,
            "program_id": self.program_id,
            "program_name": self.program.name if self.program else None,
            "campaign_id": self.campaign_id,
            "campaign_name": self.campaign.name if self.campaign else None,
            "expense_date": self.expense_date.isoformat(),
            "vendor_name": self.vendor_name,
            "document_id": self.document_id,
            "recorded_by": self.recorded_by.name,
            "status": self.status,
            "approved_by": self.approved_by.name if self.approved_by else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class Budget(db.Model):
    """An allocation of money to a Program over a period. spent/remaining
    are always derived from real Expense rows at read time (see
    budgets/service.py) — never stored, never able to drift out of sync
    with the expenses that actually happened."""

    __tablename__ = "budgets"

    id = db.Column(db.Integer, primary_key=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=False, index=True)
    period_start = db.Column(db.Date, nullable=True)
    period_end = db.Column(db.Date, nullable=True)
    allocated_amount = db.Column(db.Numeric(12, 2), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    program = db.relationship("Program")
    created_by = db.relationship("User")

    def to_dict(self, spent=None):
        data = {
            "id": self.id,
            "program_id": self.program_id,
            "program_name": self.program.name if self.program else None,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "allocated_amount": float(self.allocated_amount),
            "notes": self.notes,
            "created_by": self.created_by.name,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if spent is not None:
            remaining = float(self.allocated_amount) - spent
            data["spent"] = spent
            data["remaining"] = remaining
            data["percent_used"] = round((spent / float(self.allocated_amount)) * 100, 1) if float(self.allocated_amount) > 0 else None
        return data


class AuditLog(db.Model):
    """A minimal, general-purpose audit trail — introduced in Phase 6
    specifically for sensitive financial changes (donor edits, campaign
    status changes, expense approval/void, budget allocation, donation
    status corrections), via the single audit/service.py:log_action()
    chokepoint, same "one function every call site goes through" shape
    as notify(). before/after are JSON-serialized snapshots of only the
    fields that changed — never raw request bodies, so a payment
    credential could never end up in here even by accident (nothing in
    this app collects one in the first place, but this keeps that true
    structurally)."""

    __tablename__ = "audit_logs"
    __table_args__ = (db.Index("ix_audit_logs_resource", "resource_type", "resource_id"),)

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(30), nullable=False)
    resource_type = db.Column(db.String(30), nullable=False)
    resource_id = db.Column(db.Integer, nullable=False)
    before = db.Column(db.Text, nullable=True)
    after = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    actor = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "actor": self.actor.name,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "before": json.loads(self.before) if self.before else None,
            "after": json.loads(self.after) if self.after else None,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================
# Phase 7: Administration & Security
# ============================================================

class LoginHistory(db.Model):
    """One row per login attempt, success or failure — never a password.
    user_id is nullable because a failed attempt against an unknown email
    has no user to point at; attempted_email is kept in that case so the
    attempt is still visible to an admin reviewing security history."""

    __tablename__ = "login_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    attempted_email = db.Column(db.String(255), nullable=True)
    success = db.Column(db.Boolean, nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    failure_reason = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
            "attempted_email": self.attempted_email,
            "success": self.success,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat(),
        }


class UserSession(db.Model):
    """One row per issued refresh token — the forward-looking twin of
    RevokedToken (which is a denylist of what's dead, not a record of
    what's currently active). Revoking a session here ALSO inserts a
    RevokedToken row for the same refresh_jti (see sessions/service.py),
    so the actual JWT-blocklist enforcement never duplicates or drifts
    from what this table says is active."""

    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    refresh_jti = db.Column(db.String(36), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)

    user = db.relationship("User")

    def to_dict(self, is_current=False):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "last_seen_at": self.last_seen_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_current": is_current,
        }


class TwoFactorChallenge(db.Model):
    """A short-lived, single-use pending-login marker issued by
    POST /api/auth/login in place of real tokens when the account has
    2FA enabled — deliberately NOT a JWT (a JWT would be independently
    valid on any jwt_required()-protected route the moment it's minted,
    which is exactly the "refresh token skips 2FA" hole the platform
    spec calls out). Real access/refresh tokens are only ever minted
    after this token is redeemed via /verify-login or /recovery."""

    __tablename__ = "two_factor_challenges"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


class TotpRecoveryCode(db.Model):
    """A single one-time-use 2FA recovery code — stored hashed (same
    werkzeug generate_password_hash/check_password_hash used for account
    passwords), never in plaintext. The plaintext is shown to the user
    exactly once, at enrollment confirmation, and never again."""

    __tablename__ = "totp_recovery_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)


# ============================================================
# Phase 8: Advanced Platform Features
# ============================================================

CONSENT_TYPES = (
    "Family Portal Access", "Photo Use", "Communication", "Program Participation",
    "Data Sharing", "Emergency Contact Access",
)
CONSENT_STATUSES = ("Granted", "Denied", "Withdrawn", "Pending")


class Consent(db.Model):
    """Append-only history, not a single mutable row per (member, type) —
    granting, denying, or withdrawing consent each INSERT a new row
    rather than updating one in place (see consent/service.py:
    record_consent()). The current status for a given member+type is
    always "whichever row is newest", derived at read time
    (current_consent_status()) — this is deliberate: consent decisions
    are themselves a compliance record, and overwriting one to reflect
    the next would destroy exactly the audit trail this table exists
    to keep. AuditLog additionally records who/when for every row (see
    consent/routes.py), but this table is the durable source of truth
    even if audit_logs were ever pruned."""

    __tablename__ = "consents"
    __table_args__ = (db.Index("ix_consents_member_type", "elderly_member_id", "consent_type"),)

    id = db.Column(db.Integer, primary_key=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    consent_type = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    granted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    withdrawn_at = db.Column(db.DateTime(timezone=True), nullable=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    elderly_member = db.relationship("ElderlyMember")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "consent_type": self.consent_type,
            "status": self.status,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "withdrawn_at": self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            "recorded_by": self.recorded_by.name,
            "notes": self.notes,
            "document_id": self.document_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


FAMILY_ACCESS_STATUSES = ("Pending", "Active", "Suspended", "Revoked")


class FamilyMemberAccess(db.Model):
    """The entire authorization surface for the family portal — a family
    User (role='family') may read data about an ElderlyMember if and
    only if a row here has that exact (user_id, elderly_member_id) pair
    with access_status == 'Active' (see family/service.py:
    authorized_access(), the one function every family/routes.py
    endpoint calls before touching any member data). Unlike Consent,
    this IS a single mutable row per relationship — approve/suspend/
    revoke transition it in place, each transition audited via
    AuditLog rather than by row proliferation, since "is this
    relationship currently active" is the actual question every read
    needs answered, not "what was it in the past" (that history lives
    in audit_logs, not here)."""

    __tablename__ = "family_member_access"
    __table_args__ = (db.UniqueConstraint("user_id", "elderly_member_id", name="uq_family_access_user_member"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    relationship_label = db.Column(db.String(60), nullable=False)
    access_status = db.Column(db.String(20), nullable=False, default="Pending")
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User", foreign_keys=[user_id])
    elderly_member = db.relationship("ElderlyMember")
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "user_email": self.user.email,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "relationship": self.relationship_label,
            "access_status": self.access_status,
            "approved_by": self.approved_by.name if self.approved_by else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "created_at": self.created_at.isoformat(),
        }


class Distribution(db.Model):
    """A stock-out to a specific, named recipient — the structured layer
    Phase 8's audit found genuinely missing on top of the existing
    StockMovement ledger (which only ever carried a free-text `reason`,
    no recipient). Creating a Distribution ALSO creates the underlying
    StockMovement("Out") row in the same transaction (see
    inventory/service.py:record_distribution()) — movement_id is that
    row, so the append-only ledger stays the single source of truth for
    the actual stock balance; this table only adds "who it went to"
    on top of an entry that ledger already has."""

    __tablename__ = "distributions"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("inventory_items.id"), nullable=False, index=True)
    elderly_member_id = db.Column(db.Integer, db.ForeignKey("elderly_members.id"), nullable=False, index=True)
    program_id = db.Column(db.Integer, db.ForeignKey("programs.id"), nullable=True, index=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("stock_movements.id"), nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    distributed_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    item = db.relationship("InventoryItem")
    elderly_member = db.relationship("ElderlyMember")
    program = db.relationship("Program")
    recorded_by = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_name": self.item.name,
            "unit": self.item.unit,
            "elderly_member_id": self.elderly_member_id,
            "elderly_member_name": self.elderly_member.full_name,
            "program_id": self.program_id,
            "program_name": self.program.name if self.program else None,
            "quantity": float(self.quantity),
            "distributed_at": self.distributed_at.isoformat(),
            "recorded_by": self.recorded_by.name,
            "reason": self.reason,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


# ============================================================
# Phase 9: AI / Smart Features
# ============================================================

class AIQueryLog(db.Model):
    """The audit trail for every AI-touching request — see
    ai/service.py:log_ai_usage(), the one chokepoint every AI route goes
    through, same shape as audit.service.log_action. Deliberately does
    NOT store the raw question/prompt text or the AI's raw response:
    `query_category` is the classified intent (a fixed enum-like string,
    e.g. "VISITS_TODAY"), not free text, and `resource_ids` is a small
    JSON list of the specific record IDs the underlying deterministic
    query touched — enough to reconstruct "what did this user look at
    and when" for a security review without ever persisting personal
    data twice over. `ai_used` records whether the (optional) AI
    provider actually produced the response for this request, or the
    deterministic template fallback did."""

    __tablename__ = "ai_query_logs"
    __table_args__ = (db.Index("ix_ai_query_logs_user_created", "user_id", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    feature = db.Column(db.String(40), nullable=False)
    query_category = db.Column(db.String(40), nullable=True)
    resource_ids = db.Column(db.Text, nullable=True)
    ai_used = db.Column(db.Boolean, nullable=False, default=False)
    success = db.Column(db.Boolean, nullable=False, default=True)
    error_message = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.name,
            "feature": self.feature,
            "query_category": self.query_category,
            "resource_ids": json.loads(self.resource_ids) if self.resource_ids else [],
            "ai_used": self.ai_used,
            "success": self.success,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
        }
