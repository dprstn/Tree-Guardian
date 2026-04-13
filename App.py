import io
import re
from flask import Flask, flash, render_template, request, redirect, url_for, session, get_flashed_messages, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from database import db, User, Adoption, Observation, Observation_type, Tree, Species
from flask_mail import Mail, Message
from sqlalchemy import or_, func
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
            Observation_type.observation_report == "Disease"
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
        query = query.filter(Observation_type.observation_report == "Disease")
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
    search_query = request.args.get('search', '')
    health_filters = request.args.getlist('health')
    status_filters = request.args.getlist('status')
    species_filter = request.args.get('species', '')
    sort_order = request.args.get('sort', 'newest')

    #Join the data for the filters

    # Query multiple tables at onece
    #Tree to display Trees data and so on


    ###############################
    # from all the tables in the species get all these tables (Tree, Species, Adoption, User)
    # and specially select from Tree so each tree joins with the species
    # = JOIN species ON tree.species_id = species.species_id

    # outerjoin(Adoption) fetch all the trees even when they are not adopted
    # so it outerjoins Adoption.user_id = User.user_id

    query = db.session.query(Tree, Species, Adoption, User, func.count(Observation.observation_id).label("obs_count"))\
        .select_from(Tree)\
        .join(Species)\
        .outerjoin(Adoption)\
        .outerjoin(User)\
        .outerjoin(Observation, Tree.tree_id== Observation.tree_id)\
        .group_by(Tree.tree_id)

    if search_query:
        # ilike mworks like regex matches the most characters
        filters = [Species.species_name.ilike(f'%{search_query}%')]

        # if user searches by the tree_id
        if search_query.isdigit():
            filters.append(Tree.tree_id == int(search_query))

        query = query.filter(or_(*filters)) # the OR condition matches any filters

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

    trees = query.all()

    all_species = Species.query.all()

    return render_template('local_trees.html',
                           trees=trees,
                           all_species=all_species,
                           search_query=search_query
                           )



@app.route('/tree/<int:tree_id>')
def tree_detail(tree_id):
    return f"Tree details page for tree {tree_id}"
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

