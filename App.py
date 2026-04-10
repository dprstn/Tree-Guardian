import re
from flask import Flask, flash, render_template, request, redirect, url_for, session, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from database import db, User, Adoption, Observation, Observation_type, Tree
from flask_mail import Mail, Message
import secrets
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


mail = Mail(app)
db.init_app(app)



with app.app_context():
    db.create_all()
    admin = User(first_name = "Preston",
                 last_name = "De Sousa",
                 username = "Preston",
                 email="quietgardenercollective@gmail.com",
                 role = "admin",
                 dob=date(2004,10,4),
                 hash_password=generate_password_hash("Preston123"),
                 is_active=False,
                 email_verified=True)

    existing_admin = User.query.filter_by(username="Preston").first()

    if not existing_admin:
        db.session.add(admin)
        db.session.commit()
        print("Admin created!")

def isEmailValid(email):
    regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(regex, email) is not None

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
    get_flashed_messages()
    session.clear()
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
            session['role'] = admin.role
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
    if not session.get("is_active"):
        flash("Please login first!", "danger")
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()

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


    return render_template("homepage.html", username=user.username, role=user.role, adopted_count=adopted_count,
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

