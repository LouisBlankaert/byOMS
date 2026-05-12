from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import calendar
import os
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///byoms.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

SERVICES = [
    {'id': 'browlift_complet',   'name': 'Browlift Complet',                       'price': 30},
    {'id': 'browlift_simple',    'name': 'Browlift Simple',                        'price': 25},
    {'id': 'lashlift_complet',   'name': 'Lashlift Complet',                       'price': 30},
    {'id': 'lashlift_simple',    'name': 'Lashlift Simple',                        'price': 25},
    {'id': 'korean_lashlift',    'name': 'Korean Lashlift',                        'price': 35},
    {'id': 'manucure_japonaise', 'name': 'Manucure Japonaise',                     'price': 30},
    {'id': 'freakles',           'name': 'Freakles',                               'price': 60, 'price_from': True},
    {'id': 'grains_beaute',      'name': 'Grains de Beauté',                       'price': 15},
    {'id': 'cils_bas',           'name': 'Cils du Bas',                            'price': 5},
    {'id': 'no_wax',             'name': 'No Wax Restructuration / avec Teinture', 'price': 12},
]
SERVICES_MAP = {s['id']: s for s in SERVICES}

TIME_SLOTS = ['10:00', '11:30', '13:00', '14:30', '16:00', '17:30']
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'byoms2026')
TZ = ZoneInfo('Europe/Paris')


class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    instagram = db.Column(db.String(100), nullable=False, default='')
    email = db.Column(db.String(200), nullable=True)
    service = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time_slot = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float, nullable=False)
    paid = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UnavailableDay(db.Model):
    __tablename__ = 'unavailable_days'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)


with app.app_context():
    db.create_all()


def get_today():
    return datetime.now(TZ).date()


def get_now():
    return datetime.now(TZ)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    realisations_dir = os.path.join(app.static_folder, 'images', 'realisations')
    photos = []
    if os.path.isdir(realisations_dir):
        exts = {'.jpg', '.jpeg', '.png', '.webp'}
        photos = sorted([
            f for f in os.listdir(realisations_dir)
            if os.path.splitext(f.lower())[1] in exts
        ])
    return render_template('index.html', services=SERVICES, photos=photos)


@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        selected_date_str = request.form.get('date')
        time_slot = request.form.get('time_slot')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        instagram = request.form.get('instagram', '').strip()
        email = request.form.get('email', '').strip()
        service_id = request.form.get('service_id', '').strip()

        if not all([selected_date_str, time_slot, name, instagram, service_id]):
            flash('Veuillez remplir tous les champs.', 'error')
            return redirect(url_for('booking'))

        if service_id not in SERVICES_MAP:
            flash('Prestation invalide.', 'error')
            return redirect(url_for('booking'))

        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            flash('Date invalide.', 'error')
            return redirect(url_for('booking'))

        if UnavailableDay.query.filter_by(date=selected_date).first():
            flash('Ce jour est indisponible.', 'error')
            return redirect(url_for('booking'))

        if Reservation.query.filter_by(date=selected_date, time_slot=time_slot).first():
            flash('Ce créneau est déjà réservé.', 'error')
            return redirect(url_for('booking'))

        svc = SERVICES_MAP[service_id]

        r = Reservation(
            name=name,
            phone=phone or None,
            instagram=instagram,
            email=email or None,
            service=svc['name'],
            date=selected_date,
            time_slot=time_slot,
            price=svc['price'],
            paid=True
        )
        db.session.add(r)
        db.session.commit()

        session['last_reservation_id'] = r.id
        return redirect(url_for('confirmation'))

    return render_template('booking.html', services=SERVICES)


@app.route('/confirmation')
def confirmation():
    rid = session.get('last_reservation_id')
    if not rid:
        return redirect(url_for('booking'))
    r = Reservation.query.get(rid)
    if not r:
        return redirect(url_for('booking'))
    return render_template('confirmation.html', reservation=r)


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/api/availability')
def api_availability():
    date_str = request.args.get('date')
    if not date_str:
        return jsonify({'error': 'Missing date'}), 400
    try:
        req_date = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({'error': 'Invalid date'}), 400

    if UnavailableDay.query.filter_by(date=req_date).first():
        return jsonify({s: False for s in TIME_SLOTS})

    reservations = Reservation.query.filter_by(date=req_date).all()
    booked = {r.time_slot for r in reservations}
    now = get_now()
    today = now.date()

    availability = {}
    for slot in TIME_SLOTS:
        if slot in booked:
            availability[slot] = False
        elif req_date == today:
            slot_dt = datetime.combine(req_date, datetime.strptime(slot, '%H:%M').time()).replace(tzinfo=TZ)
            availability[slot] = slot_dt > now
        else:
            availability[slot] = True

    return jsonify(availability)


@app.route('/api/unavailable-month')
def api_unavailable_month():
    month_str = request.args.get('month')
    try:
        month_date = date.fromisoformat(month_str + '-01')
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid month'}), 400

    _, days = calendar.monthrange(month_date.year, month_date.month)
    month_end = date(month_date.year, month_date.month, days)

    blocked = UnavailableDay.query.filter(
        UnavailableDay.date >= month_date,
        UnavailableDay.date <= month_end
    ).all()
    blocked_set = {ud.date.isoformat() for ud in blocked}

    unavailable = list(blocked_set)
    for day_num in range(1, days + 1):
        day = date(month_date.year, month_date.month, day_num)
        iso = day.isoformat()
        if iso not in blocked_set:
            booked_count = Reservation.query.filter_by(date=day).count()
            if booked_count >= len(TIME_SLOTS):
                unavailable.append(iso)

    return jsonify({'unavailable': unavailable})


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Mot de passe incorrect.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    month_str = request.args.get('month')
    today = get_today()

    if month_str:
        try:
            current_month = date.fromisoformat(month_str + '-01')
        except ValueError:
            current_month = today.replace(day=1)
    else:
        current_month = today.replace(day=1)

    _, days_in_month = calendar.monthrange(current_month.year, current_month.month)
    month_start = current_month
    month_end = date(current_month.year, current_month.month, days_in_month)

    reservations = Reservation.query.filter(
        Reservation.date >= month_start,
        Reservation.date <= month_end
    ).order_by(Reservation.date, Reservation.time_slot).all()

    unavailable_days = UnavailableDay.query.filter(
        UnavailableDay.date >= month_start,
        UnavailableDay.date <= month_end
    ).all()
    unavailable_dates = {ud.date for ud in unavailable_days}

    cal = calendar.monthcalendar(current_month.year, current_month.month)

    reservations_by_date = {}
    for r in reservations:
        reservations_by_date.setdefault(r.date, []).append(r)

    prev_month = (current_month - timedelta(days=1)).replace(day=1)
    next_month = (month_end + timedelta(days=1)).replace(day=1)

    MONTHS_FR = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
                 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

    return render_template('admin/dashboard.html',
                           current_month=current_month,
                           cal=cal,
                           reservations_by_date=reservations_by_date,
                           unavailable_dates=unavailable_dates,
                           all_reservations=reservations,
                           time_slots=TIME_SLOTS,
                           today=today,
                           prev_month=prev_month,
                           next_month=next_month,
                           months_fr=MONTHS_FR,
                           days_in_month=days_in_month)


@app.route('/admin/reservations')
@admin_required
def admin_reservations():
    reservations = Reservation.query.order_by(Reservation.date.desc(), Reservation.time_slot.desc()).all()
    return render_template('admin/reservations.html', reservations=reservations, today=get_today())


@app.route('/admin/delete', methods=['POST'])
@admin_required
def admin_delete():
    r = Reservation.query.get(request.form.get('reservation_id'))
    if r:
        db.session.delete(r)
        db.session.commit()
    month = request.form.get('month', '')
    return redirect(url_for('admin_dashboard', month=month) if month else url_for('admin_dashboard'))


@app.route('/admin/move', methods=['POST'])
@admin_required
def admin_move():
    r = Reservation.query.get(request.form.get('reservation_id'))
    if not r:
        return jsonify({'error': 'Réservation non trouvée'}), 404

    try:
        new_date = date.fromisoformat(request.form.get('new_date', ''))
    except ValueError:
        return jsonify({'error': 'Date invalide'}), 400

    new_slot = request.form.get('new_slot')

    if UnavailableDay.query.filter_by(date=new_date).first():
        return jsonify({'error': 'Ce jour est indisponible'}), 400

    if Reservation.query.filter(
        Reservation.date == new_date,
        Reservation.time_slot == new_slot,
        Reservation.id != r.id
    ).first():
        return jsonify({'error': 'Ce créneau est déjà réservé'}), 400

    r.date = new_date
    r.time_slot = new_slot
    db.session.commit()

    return jsonify({'success': True})


@app.route('/admin/toggle-day', methods=['POST'])
@admin_required
def admin_toggle_day():
    try:
        toggle_date = date.fromisoformat(request.form.get('date', ''))
    except ValueError:
        return jsonify({'error': 'Date invalide'}), 400

    existing = UnavailableDay.query.filter_by(date=toggle_date).first()
    if existing:
        count = Reservation.query.filter_by(date=toggle_date).count()
        if count > 0 and request.form.get('confirm') != 'yes':
            return jsonify({'requires_confirm': True, 'count': count})
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'status': 'available'})
    else:
        db.session.add(UnavailableDay(date=toggle_date))
        db.session.commit()
        return jsonify({'status': 'unavailable'})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
