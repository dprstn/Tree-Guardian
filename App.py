import csv
import io
import re
from flask import Flask, flash, render_template, request, redirect, url_for, session, get_flashed_messages, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta, timezone
from database import db, User, Adoption, Observation, Observation_type, Tree, Species, Tag, TreeTag
from flask_mail import Mail, Message
from sqlalchemy import or_, func, case
import qrcode
import secrets

import os
from werkzeug.utils import  secure_filename # more security for files
import uuid

app = Flask(__name__)
app.secret_key = 'quiet_gardeners'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TreeGuardian.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# EMAIL CONFIGURATION

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'quietgardenercollective@gmail.com'
app.config['MAIL_PASSWORD'] = 'kotn ilrf ewoe qmvd'
app.config['MAIL_DEFAULT_SENDER'] = 'quietgardenercollective@gmail.com'

UPLOAD_FOLDER = 'static/uploads/trees'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = "static/uploads/trees"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BASE_URL = os.environ.get("BASE_URL", "https://127.0.0.1:5000")

REQUIRED_COLUMNS = {
    'species_name', 'latitude', 'longitude',
    'planting_date', 'age', 'tree_size', 'health_status'
}
VALID_HEALTH = {'Healthy', 'Needs Attention', 'Critical'}
MAX_ERROR_DISPLAY = 10

mail = Mail(app)
db.init_app(app)



with app.app_context():
    db.create_all()
    existing_admin = User.query.filter_by(username="Preston").first()

    if Species.query.count() == 0:
        species_list = [
            Species(species_name="Oak"),
            Species(species_name="Maple"),
            Species(species_name="Pine"),
            Species(species_name="Birch"),
            Species(species_name="Cherry")
        ]
        db.session.add_all(species_list)
        db.session.commit()
        print("All types of Species Added!")

    if not existing_admin:
        admin = User(first_name = "Preston",
                     last_name = "De Sousa",
                     username = "Preston",
                     email="quietgardenercollective@gmail.com",
                     role = "admin",
                     dob=date(2004,10,4),
                     hash_password=generate_password_hash("Preston123"),
                     is_active=False,
                     email_verified=True)

        db.session.add(admin)
        db.session.commit()
        print("ADMIN CREATED !!")

    if Observation_type.query.count() == 0:
        obs_types = [
            Observation_type(observation_category="Wildlife", observation_report="Wildlife Sighting"),
            Observation_type(observation_category="Disease", observation_report="Health Alert / Disease"),
        ]
        db.session.add_all(obs_types)
        db.session.commit()
        print("Observation types seeded!")




    else:
        if existing_admin.role != "admin":
            existing_admin.role = "admin"
            db.session.commit()
            print("------PRESTON ROLE UPDATED TO ADMIN")

        else:
            print("----------PRESTON IS ALREADY ADMIN")


def isEmailValid(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('signup.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name'].strip('')
        last_name = request.form['last_name'].strip('')
        username = request.form['username'].strip('')
        password = request.form['password'].strip('')
        dob = request.form['dob'].strip('')
        email = request.form['email'].strip('')

        if not first_name and not last_name and not password and not username and not dob and not email:
            flash("All fields are required!")

        elif not isEmailValid(email):
            flash("Invallid email format! Please use correct format user@example.com", "danger")
        elif not first_name:
            flash("Please enter first name", "danger")
        elif not last_name:
            flash("Please enter last name", "danger")
        elif not username:
            flash("Please enter username", "danger")
        elif not password:
            flash("Please enter password", "danger")

        elif not dob:
            flash("Please enter date of birth", "danger")
        elif not date_of_birth_is_valid(dob):
            flash("Invalid Date of Birth!", "danger")

        else:

            existing_user = User.query.filter_by(username=username).first()
            existing_email = User.query.filter_by(email=email).first()



            if existing_user:
                flash(f"Username  {username} already exist", "danger")


            elif existing_email:

                if not existing_email.email_verified:
                    db.session.delete(existing_email)
                    db.session.commit()
                else:
                    flash("Email already exists", "danger")
                    return render_template('register.html')

            else:
                token =secrets.token_urlsafe(32)

                hashed_password = generate_password_hash(password)

                register_user = User(first_name=first_name,
                                     last_name=last_name,
                                     username=username,
                                     email=email,
                                     role='user',
                                     dob=datetime.strptime(dob, "%Y-%m-%d").date(),
                                     hash_password=hashed_password,
                                     is_active=False,
                                     verification_token=token,
                                     email_verified=False,
                                     token_created_at=datetime.now())

                db.session.add(register_user)
                db.session.commit()

                try:
                    msg = Message("Verify your Tree Guardian Account", recipients=[email])

                    link = url_for('verify_email', token=token, _external=True)
                    msg.body = f"Hello {first_name}! Thank you for registering. Click here to verify: {link}"
                    mail.send(msg)
                    flash("Please check your email to verify your account.", "success")
                except Exception as e:
                    print(f"Mail error: {e}")
                    flash("We couldn't send the verification email", "warning")




                return redirect(url_for('login'))
    return  render_template('register.html')




def date_of_birth_is_valid(dob):
    if not dob or len(dob) < 10:
        return False

    if dob.count('-') != 2:
        return False

    try:
        year, month, day = dob.split('-')

        yyyy = int(year)
        mm = int(month)
        dd = int(day)

        if dd < 1 or dd > 31:
            return False

        if mm < 1 or mm > 12:
            return False

        if yyyy < 1940 or yyyy > 2025:
            return False

    except ValueError:
        return False

    return True

@app.route('/verify/<token>')
def verify_email(token):
    #get_flashed_messages()
    #session.clear()
    user = User.query.filter_by(verification_token=token).first()
    if user:
        time_diff = datetime.now() - user.token_created_at
        if time_diff.total_seconds() > 86400:#= 24 hours
            db.session.delete(user)
            db.session.commit()
            flash("Verification link expired. Please register again ", "danger")
            return redirect(url_for('register'))
        user.email_verified = True
        user.verification_token = None
        db.session.commit()
        flash("Email verified successfully! You can now log in.", "success")
        return redirect(url_for('login'))
    else:
        flash("Invalid link or already verified.", "danger")
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get("is_active"):
        return redirect(url_for('homepage'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username and not password:
            flash("All fields are required!")

        elif not username:
            flash("Please enter username", "danger")
        elif not password:
            flash("Please enter password", "danger")

        else:
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and check_password_hash(existing_user.hash_password, password):

               if not existing_user.email_verified:
                   flash("Please verify your email address before logging in.", "warning")
                   return redirect(url_for('login'))

               #saving user session
               session['username'] = existing_user.username
               session['role'] = existing_user.role
               session['is_active'] = True
               existing_user.is_active = True
               db.session.commit()
               flash(f"Logged in successfully, Welcome back {session['username']}")

               return redirect(url_for('homepage'))
            else:
                flash("Invalid username or password", "danger")

    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()

        if not username and not password:
            flash("All fields are required!")


        elif not username:
            flash("Please enter username", "danger")
        elif not password:
            flash("Please enter password", "danger")


        admin = User.query.filter_by(username=username, role='admin').first()
        if admin and check_password_hash(admin.hash_password, password):
            # saving user session
            session['username'] = admin.username
            session['role'] = "admin"
            session['is_active'] = True
            admin.is_active = True
            db.session.commit()
            flash(f"Welcome back Admin {session['username']}")

            return redirect(url_for('homepage'))
        else:
            flash("Invalid username or password", "danger")


    return render_template('admin_login.html')


@app.route('/homepage')
def homepage():
    if not session.get("is_active") or "username" not in session:
        flash("Please login first!", "danger")
        return redirect(url_for('login'))


    user = User.query.filter_by(username=session['username']).first()
    if not user:
        session.clear()
        return redirect(url_for('login'))
    if user.role != "admin" and user.username == "Preston":
        user.role = "admin"
        db.session.commit()
    print(f"DEBUG: user {user.username} has a role {user.role}")

    adopted_count = Adoption.query.filter_by(user_id=user.user_id).count()

    total_trees_in_db = Tree.query.count()

    #3. getting list of all the trees the user has adopted and list of trees IDs to filter observations

    my_adoptions = Adoption.query.filter_by(user_id=user.user_id).all()
    my_tree_ids = [adopt.tree_id for adopt in my_adoptions]

    if my_tree_ids:
        # total observation made on user trees by anyone
        obs_count = Observation.query.filter(Observation.tree_id.in_(my_tree_ids)).count()

        # for wildlife sightings on your trees

        wildlife_count = db.session.query(Observation).join(Observation_type).filter(
            Observation.tree_id.in_(my_tree_ids),
            Observation_type.observation_category == "Wildlife"
        ).count()


    ######################## DISEASE REPORT ############################
        disease_count = db.session.query(Observation).join(Observation_type).filter(
            Observation.tree_id.in_(my_tree_ids),
            Observation_type.observation_category == "Disease"
        ).count()
    else:
        # If user hasn't adopted any trees yet then set everything to 0
        obs_count, wildlife_count, disease_count = 0, 0, 0


    return render_template("homepage.html", username=user.username, role=user.role.lower() if user.role else 'user', adopted_count=adopted_count,
                           total_trees_in_db=total_trees_in_db,
                           obs_count=obs_count,
                           wildlife_count=wildlife_count,
                           disease_count=disease_count)


@app.route('/observation_details/<obs_type>')
def observation_details(obs_type):
    if not session.get("is_active"):
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    my_adoptions = Adoption.query.filter_by(user_id=user.user_id).all()
    my_tree_ids = [adopt.tree_id for adopt in my_adoptions]


    query = db.session.query(Observation).join(Observation_type).filter(
        Observation.tree_id.in_(my_tree_ids)
    )

    #3. Filter the list based on which card was clicked.

    if obs_type == "wildlife":
        query = query.filter(Observation_type.observation_category == "Wildlife")
        title = "Wildlife Sightings"

    elif obs_type == "disease":
        query = query.filter(Observation_type.observation_category == "Disease")
        title = "Health Alerts"

    else:
        title = "All Observations"

    notes = query.all()

    return render_template("notes_list.html", notes=notes, title=title)

@app.route('/add_tree', methods=['GET', 'POST'])
def add_tree():
    if not session.get("is_active") or session.get('role') != 'admin':
        flash("Unathorised access!", "danger")
        return redirect(url_for('homepage'))

    if request.method == "POST":
        species_id = request.form.get('species_id', '').strip()
        age = request.form.get('age', '').strip()
        tree_size = request.form.get('tree_size', '').strip()
        health = request.form.get('health_status', '').strip()

        latitude = request.form.get('latitude', '').strip()
        longitude = request.form.get('longitude', '').strip()
        planting_date = request.form.get('planting_date', '').strip()
        notes = request.form.get('notes', '').strip()

        if not all([species_id, age, tree_size, health, latitude, longitude]):
            flash("All fields are required", "danger")
            return redirect(url_for('add_tree'))

        if not planting_date:
            flash("Planting date is required", "danger")

        try:
            age = int(age)
            size = float(tree_size)
            latitude = float(latitude)
            longitude = float(longitude)

            if size <= 0 or age < 0:
                raise  ValueError

        except ValueError:
            flash("Invalid numeric input (age, size, location)", "danger")
            return redirect(url_for('add_tree'))

        species = Species.query.get(int(species_id))
        if not species:
            flash("Invalid species selected", "danger")
            return  redirect(url_for('add_tree'))

        planting = None

        if planting_date:
            try:
                planting =datetime.strptime(planting_date, '%Y-%m-%d').date()

            except ValueError:
                flash("Invalid date format", "danger")
                return redirect(url_for('add_tree'))




        file = request.files.get('photo')
        image_url = None

        if file and file.filename != '':
            if not allowed_file(file.filename):
                flash("Invalid file type. Only JPG/PNG allowed.", "danger")
                return redirect(url_for('add_tree'))
            filename = f"{uuid.uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image_url = f"static/uploads/trees/{filename}"

        try:
            tree = Tree(
                species_id = species.species_id, latitude=latitude, longitude=longitude,
                age=age, tree_size=size, health_status=health,
                image_url=image_url, notes=notes, planting_date=planting
            )
            db.session.add(tree)
            db.session.commit()
            flash("Tree added successfully!", "tree")
            return redirect(url_for('add_tree'))

        except Exception as e:
            db.session.rollback()
            flash(f"Database error: {str(e)}", "danger")

    return render_template('add_tree.html', species_list=Species.query.all())

@app.route('/qr/<int:tree_id>')

def generate_qr(tree_id):
    url = f"{BASE_URL}/tree/{tree_id}"

    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True) #QR is optimised auto-adjusted

    img = qr.make_image(fill_color='#0b422a', back_color="white") # dark green plus white background

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype="image/png")

@app.route('/local_trees')
def local_trees():
    if not session.get("is_active"):
        return redirect(url_for('login'))



    # request.args gets data from query string (? search = oak)
    search_query = request.args.get('search', '').strip().lower()
    health_filters = request.args.getlist('health')
    status_filters = request.args.getlist('status')
    species_filter = request.args.get('species', '')
    sort_order = request.args.get('sort', 'newest')
    tag_filter = request.args.get('tag')

    #Join the data for the filters

    # Query multiple tables at onece
    #Tree to display Trees data and so on


    ###############################
    # from all the tables in the species get all these tables (Tree, Species, Adoption, User)
    # and specially select from Tree so each tree joins with the species
    # = JOIN species ON tree.species_id = species.species_id

    # outerjoin(Adoption) fetch all the trees even when they are not adopted
    # so it outerjoins Adoption.user_id = User.user_id
    latest_obs_sq = db.session.query(
        Observation.tree_id,
        func.max(Observation.observed_time).label('last_observed')
    ).group_by(Observation.tree_id).subquery()

    query = db.session.query(
        Tree, Species, Adoption, User,
        func.coalesce(func.count(Observation.observation_id), 0).label("obs_count"),
        latest_obs_sq.c.last_observed
    )\
        .select_from(Tree)\
        .join(Species)\
        .outerjoin(Adoption)\
        .outerjoin(User)\
        .outerjoin(Observation, Tree.tree_id == Observation.tree_id)\
        .outerjoin(latest_obs_sq, Tree.tree_id == latest_obs_sq.c.tree_id)\
        .group_by(Tree.tree_id, latest_obs_sq.c.last_observed)

    health_priority = case(
        {
            'Critical' : 1,
            'Needs Attention' : 2,
            'Healthy': 3,
        },
        value=Tree.health_status,
        else_=4
    )
    query = query.order_by(health_priority, Tree.tree_id.desc())

    if tag_filter:
        query = query.join(Tree.tags).filter(Tag.name == tag_filter)

    elif search_query:

        if search_query.startswith("#") and len(search_query) > 1:
            tag_name = search_query.replace("#", "")
            query = query.join(Tree.tags) \
                .filter(Tag.name.ilike(f"%{tag_name}%"))

        # ilike mworks like regex matches the most characters

        else:
            filters = [Species.species_name.ilike(f'%{search_query}%')]

            # if user searches by the tree_id
            if search_query.isdigit():

                filters.append(Tree.tree_id == int(search_query))

            query = query.outerjoin(Tree.tags).filter(
                or_(
                    *filters,
                    Tag.name.ilike(f"%{search_query}%")
                )
            ) # the OR condition matches any filters

    if health_filters:
        query = query.filter(Tree.health_status.in_(health_filters))

    if species_filter:

        query = query.filter(Tree.species_id == int(species_filter))

    if status_filters: #here
        if 'available' in status_filters and 'adopted' not in status_filters:

            query = query.filter(Adoption.adoption_id.is_(None))
            # if the adoption id is null then its available
        elif 'adopted' in status_filters and 'available' not in status_filters:
            query = query.filter(Adoption.adoption_id.is_not(None))



    if sort_order == 'oldest':
        query = query.order_by(Tree.tree_id.asc())

    elif sort_order == 'newest':
        query = query.order_by(Tree.tree_id.desc())

    elif sort_order == "age_oldest":
        query = query.order_by(Tree.age.desc())

    elif sort_order == "age_youngest":
        query = query.order_by(Tree.age.asc())

    #returns list of all results:

    query = query.distinct()
    trees = query.all()

    all_tags = Tag.query.all()

    all_species = Species.query.all()
    tree_count = len(trees)

    all_trees = query.all()

    page = request.args.get('page', 1, type=int)
    per_page = 3


    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    trees_on_page = pagination.items
    return render_template('local_trees.html',
                           trees=trees_on_page, # use for cards
                           all_trees=all_trees,
                           pagination=pagination,
                           now=datetime.now(),
                           search_query=search_query,
                           all_species=all_species,
                           all_tags=all_tags,
                           tree_count=Tree.query.count(),

                           )



@app.route('/tree/<int:tree_id>')
def tree_detail(tree_id):
    if not session.get("is_active"):
        return redirect(url_for('login'))

    tree_data = db.session.query(Tree, Species).join(Species).filter(Tree.tree_id == tree_id).first_or_404()
    tree, species = tree_data

    adoption_data = db.session.query(Adoption, User).outerjoin(User, Adoption.user_id == User.user_id).filter(Adoption.tree_id == tree_id).first()

    if adoption_data:
        adoption, adopted_user = adoption_data

    else:
        adoption, adopted_user = None, None

    #fetching observations with user info and type
    observations = db.session.query(Observation, User, Observation_type)\
        .join(User, Observation.user_id == User.user_id)\
        .join(Observation_type, Observation.observation_type_id == Observation_type.observation_type_id)\
        .filter(Observation.tree_id == tree_id)\
        .order_by(Observation.observed_time.desc()).all()

    obs_count = db.session.query(func.count(Observation.observation_id))\
                .filter(Observation.tree_id == tree_id).scalar()

    return render_template('tree_detail.html',
                           tree=tree,
                           species=species,
                           adoption=adoption,
                           adopted_user=adopted_user,
                           observations=observations,
                           obs_count=obs_count)


@app.route('/adopt_tree/<int:tree_id>', methods=['POST'])
def adopt_tree(tree_id):
    if not session.get("is_active"):
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

    existing =  Adoption.query.filter_by(tree_id=tree_id).first()


    if not existing:

        new_adoption = Adoption(
            tree_id=tree_id,
            user_id=user.user_id,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365)

        )
        db.session.add(new_adoption)
        db.session.commit()


    return  redirect(url_for('tree_detail', tree_id=tree_id))

@app.route('/add_observation/<int:tree_id>', methods=['POST'])
def add_observation(tree_id):
    if not session.get("is_active"): return redirect(url_for('login'))
    user = User.query.filter_by( username=session['username']).first()
    if not user:
        return redirect(url_for('login'))

    health_update = request.form.get('health_status')

    obs_type_val = request.form.get('obs_type')

    notes = request.form.get('notes', '').strip()
    import re
    tags_input = request.form.get('tags', '')
    tags = re.findall(r"#(\w+)", tags_input.lower())




    if not notes:
        flash("Please provide notes.", 'danger')
        return redirect(url_for('tree_detail', tree_id=tree_id))

    obs_type_obj = Observation_type.query.filter_by(observation_category=obs_type_val).first()

    if not obs_type_obj:
        obs_type_obj = Observation_type(observation_category=obs_type_val, observation_report=obs_type_val)
        db.session.add(obs_type_obj)
        db.session.commit()

    if obs_type_val == "Disease" and not health_update:
        flash("Please select a health status for health alerts.", "danger")
        return redirect(url_for('tree_detail', tree_id=tree_id))


    if obs_type_val == "Disease" and health_update:
        tree = Tree.query.get(tree_id)
        tree.health_status = health_update

    image_path = None
    file = request.files.get('photo')
    if file and file.filename:
        filename = secure_filename(file.filename)
        file_path = f"uploads/trees/{filename}"
        full_path = os.path.join('static', file_path)
        file.save(full_path)
        image_path = file_path
    new_obs = Observation(
        tree_id = tree_id,
        user_id = user.user_id,
        observation_type_id=obs_type_obj.observation_type_id,
        notes=notes,
        image_url=image_path,
        observed_time=datetime.now()

    )

    for tag_name in tags:
        tag = Tag.query.filter_by(name=tag_name).first()

        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
            db.session.commit()

        existing = TreeTag.query.filter_by(
            tree_id=tree_id,
            tag_id=tag.tag_id
        ).first()

        if not existing:
            db.session.add(TreeTag(tree_id=tree_id, tag_id=tag.tag_id))




    db.session.add(new_obs)
    db.session.commit()
    if image_path:
        tree = Tree.query.get(tree_id)
        if tree:
            tree.image_url = image_path
            db.session.commit()
    flash("Observation added to the community feed!", "success")
    return redirect(url_for('tree_detail', tree_id=tree_id))


@app.route('/edit_tree/<int:tree_id>', methods=['GET', 'POST'])
def edit_tree(tree_id):
    if session.get("role") != "admin":
        return  redirect(url_for('local_trees'))

    tree = Tree.query.get_or_404(tree_id)

    if request.method == "POST":
        tree.tree_size = request.form.get('tree_size')
        tree.age = request.form.get('age')
        tree.health_status = request.form.get('health_status')

        tree.latitude = request.form.get('latitude')
        tree.longitude = request.form.get('longitude')

        # photo handling

        photo = request.files.get('photo')
        if photo and photo.filename:
            # delete old photo from disk if it exists
            if tree.image_url:
                old_path = os.path.join('static', tree.image_url.split('static/')[-1])
                if os.path.exists(old_path):
                    os.remove(old_path)

            # save new photo
            ext = os.path.splitext(secure_filename(photo.filename))[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join('static', 'uploads', 'trees', filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            photo.save(save_path)
            tree.image_url = f"static/uploads/trees/{filename}"



        db.session.commit()

        flash('Tree updated successfully!', "success")
        return redirect(url_for('local_trees', tree_id=tree_id))

    return render_template('edit_tree.html', tree=tree, species_list=Species.query.all())
@app.route('/events')
def events():
    if not session.get("is_active"):
        return redirect(url_for('login'))

    return render_template('events.html')

@app.route('/export_trees')
def export_trees():
    if session.get('role') != "admin":
        flash("Unauthorised access!", "danger")
        return redirect(url_for('local_trees'))
    trees = db.session.query(Tree, Species)\
        .join(Species, Tree.species_id == Species.species_id).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        'species_name', 'latitude', 'longitude',
        'planting_date', 'age', 'tree_size',
        'health_status', 'notes', 'tags',
        'obs_notes', 'obs_type','obs_image','image_url', 'adopted_user'
    ])

    # paste this temporarily before your loop


    for tree, species in trees:
        print(f"Looking for obs with tree_id={tree.tree_id}, type={type(tree.tree_id)}")

        observations = Observation.query \
            .filter(Observation.tree_id == tree.tree_id) \
            .order_by(Observation.observed_time.asc()) \
            .all()

        print(f"observations = {observations}")


        adoption = Adoption.query.filter_by(tree_id=tree.tree_id).first()
        adopted_user = ''
        if adoption:
            user = User.query.get(adoption.user_id)
            if user:
                adopted_user = user.username
        tag_names = ' '.join(f"#{t.name}" for t in tree.tags) if tree.tags else ''
        if observations:
            # one row per observation
            for obs in observations:
                writer.writerow([
                    species.species_name,
                    tree.latitude,
                    tree.longitude,
                    tree.planting_date.strftime('%Y-%m-%d') if tree.planting_date else '',
                    tree.age,
                    tree.tree_size,
                    tree.health_status,
                    tree.notes or '',
                    tag_names,
                    obs.notes,
                    obs.observation_type_id,
                    obs.image_url or '',
                    tree.image_url or '',
                    adopted_user
                ])
        else:
            # no observations — still export the tree with blank obs fields
            writer.writerow([
                species.species_name,
                tree.latitude,
                tree.longitude,
                tree.planting_date.strftime('%Y-%m-%d') if tree.planting_date else '',
                tree.age,
                tree.tree_size,
                tree.health_status,
                tree.notes or '',
                tag_names,
                '',
                '',
                tree.image_url or '',
                adopted_user
            ])



    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'trees_export_{date.today().strftime("%Y%m%d")}.csv'
    )

@app.route('/import_trees', methods=['POST'])

def import_trees():
    if session.get('role') != 'admin':
        flash("Unauthorised access!", "danger")
        return redirect(url_for('local_trees'))

    file = request.files.get('csv_file')
    if not file or not file.filename.endswith('.csv'):
        flash("Please upload a valid .csv file.", "danger")
        return redirect(url_for('local_trees'))

    file_data = file.read()
    if len(file_data) > 2 * 1024 * 1024:
        flash("File too large (max 2MB)", "danger")
        return redirect(url_for('local_trees'))

    success_count = 0
    skipped_count = 0
    errors = []

    try:
        stream = io.StringIO(file_data.decode('utf-8', errors='ignore'))
        reader = csv.DictReader(stream)

        if not reader.fieldnames:
            flash("CSV file is empty or has no headers.", "danger")
            return redirect(url_for('local_trees'))

        actual_cols = {c.strip().lower() for c in reader.fieldnames}
        missing = {c for c in REQUIRED_COLUMNS if c not in actual_cols}
        if missing:
            flash(f"CSV is missing required columns: {', '.join(sorted(missing))}", "danger")
            return redirect(url_for('local_trees'))

        for row_num, row in enumerate(reader, start=2):
            print(f"\n--- Processing Row {row_num} ---")
            row = {k.strip().lower(): (v.strip() if v else '') for k, v in row.items()}

            missing_fields = [f for f in REQUIRED_COLUMNS if not row.get(f)]
            if missing_fields:
                errors.append(f"Row {row_num}: missing {', '.join(missing_fields)} – skipped")
                skipped_count += 1
                continue

            species_name = row['species_name']
            species = Species.query.filter(Species.species_name.ilike(species_name)).first()
            if not species:
                species = Species(species_name=species_name)
                db.session.add(species)
                db.session.flush()

            try:
                latitude = float(row['latitude'])
                longitude = float(row['longitude'])
                age = int(row['age'])
                tree_size = float(row['tree_size'])
                if tree_size <= 0 or age < 0:
                    raise ValueError
            except ValueError:
                errors.append(f"Row {row_num}: invalid numeric value – skipped")
                skipped_count += 1
                continue

            date_str = row['planting_date']
            try:
                planting_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    planting_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                except ValueError:
                    errors.append(f"Row {row_num}: bad planting_date format – skipped")
                    skipped_count += 1
                    continue

            health = row['health_status']
            if health not in VALID_HEALTH:
                errors.append(f"Row {row_num}: health_status '{health}' not valid – skipped")
                skipped_count += 1
                continue

            existing = Tree.query.join(Species).filter(
                Species.species_name.ilike(species_name),
                Tree.latitude == latitude,
                Tree.longitude == longitude,
                Tree.planting_date == planting_date
            ).first()

            # if tree already exists just add the observation, don't create a new tree
            if existing:
                obs_notes = row.get('obs_notes', '').strip("()").replace("'", "").replace('"', '').strip()
                obs_type_raw = row.get('obs_type', '').strip()

                if obs_notes and obs_type_raw and obs_type_raw.isdigit():
                    obs_type_id = int(obs_type_raw)
                    obs_type_exists = Observation_type.query.filter_by(observation_type_id=obs_type_id).first()

                    if obs_type_exists:
                        user = User.query.filter_by(username=session.get('username')).first()

                        duplicate_obs = Observation.query.filter_by(
                            tree_id=existing.tree_id,
                            notes=obs_notes,
                            observation_type_id=obs_type_id
                        ).first()

                        if not duplicate_obs and user:
                            new_obs = Observation(
                                tree_id=existing.tree_id,
                                notes=obs_notes,
                                observed_time=datetime.now(),
                                user_id=user.user_id,
                                observation_type_id=obs_type_id,
                                image_url=row.get('obs_image', '').strip() or None
                            )
                            db.session.add(new_obs)
                            print(f"Observation added to existing tree {existing.tree_id}")
                        else:
                            print(f"Duplicate observation skipped for tree {existing.tree_id}")

                skipped_count += 1  # ← inside if existing
                errors.append(f"Row {row_num}: duplicate entry (Tree ID #{existing.tree_id}) – skipped")
                continue  # skip creating a new tree
            image_url = row.get('image_url', '').strip()

            # only use it if the file actually exists on disk
            if image_url:
                full_path = os.path.join('static', image_url)
                if not os.path.exists(full_path):
                    print(f"Row {row_num}: image file not found on disk — image skipped")
                    image_url = ''


            new_tree = Tree(
                species_id=species.species_id,
                latitude=latitude,
                longitude=longitude,
                planting_date=planting_date,
                age=age,
                tree_size=tree_size,
                health_status=health,
                notes=row.get('notes', ''),
                image_url=image_url
            )
            db.session.add(new_tree)
            db.session.flush()

            # --- OBSERVATION ---
            obs_notes = row.get('obs_notes', '').strip("()").replace("'", "").replace('"', '').strip()
            obs_type_raw = row.get('obs_type', '').strip()

            if obs_notes and obs_type_raw and obs_type_raw.isdigit():
                obs_type_id = int(obs_type_raw)

                # CHECK the obs_type_id actually exists in the database
                obs_type_exists = Observation_type.query.filter_by(observation_type_id=obs_type_id).first()
                print(f"obs_type_id={obs_type_id}, exists={obs_type_exists}")

                if not obs_type_exists:
                    print(f"Row {row_num}: observation_type_id {obs_type_id} does not exist in DB — skipping observation")
                    errors.append(f"Row {row_num}: obs_type {obs_type_id} not found in database — observation skipped")
                else:
                    user = User.query.filter_by(username=session.get('username')).first()
                    if user:
                        new_obs = Observation(
                            tree_id=new_tree.tree_id,
                            notes=obs_notes,
                            observed_time=datetime.now(),
                            user_id=user.user_id,
                            observation_type_id=obs_type_id,
                            image_url=row.get('obs_image', '').strip() or None
                        )
                        db.session.add(new_obs)
                        print(f"Observation added for tree {new_tree.tree_id}")
                    else:
                        print(f"Row {row_num}: user not found in session — observation skipped")

            # --- ADOPTION ---
            adopted_username = row.get('adopted_user', '')
            if adopted_username:
                user = User.query.filter(User.username.ilike(adopted_username.strip())).first()
                if user:
                    new_adoption = Adoption(
                        tree_id=new_tree.tree_id,
                        user_id=user.user_id,
                        start_date=date.today(),
                        end_date=date.today().replace(year=date.today().year + 1)
                    )
                    db.session.add(new_adoption)

            # --- TAGS ---
            raw_tags = row.get('tags', '')
            if raw_tags:
                tag_names = raw_tags.replace(',', ' ').split()
                for tag_name in tag_names:
                    tag_name = tag_name.replace('#', '').lower().strip()
                    if not tag_name:
                        continue
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                        db.session.flush()
                    link = TreeTag.query.filter_by(tree_id=new_tree.tree_id, tag_id=tag.tag_id).first()
                    if not link:
                        db.session.add(TreeTag(tree_id=new_tree.tree_id, tag_id=tag.tag_id))

            success_count += 1

        print("\n=== IMPORT SUMMARY ===")
        print(f"Success: {success_count}")
        print(f"Skipped: {skipped_count}")
        for e in errors:
            print(e)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f" IMPORT ERROR: {str(e)}")
        flash(f"Import failed: {str(e)}", "danger")
        return redirect(url_for('local_trees'))

    more_errors = max(0, len(errors) - MAX_ERROR_DISPLAY)
    session['import_feedback'] = {
        'success': success_count,
        'skipped': skipped_count,
        'errors': errors[:MAX_ERROR_DISPLAY],
        'more_errors': more_errors
    }
    return redirect(url_for('local_trees'))
@app.route('/logout')
def logout():
    username = session.get('username')
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            user.is_active = False
            db.session.commit()
    session.clear()

    return redirect(url_for('home'))
if __name__ == "__main__":
    app.run(debug=True)

