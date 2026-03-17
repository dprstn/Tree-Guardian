from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from database import db, User

app = Flask(__name__)
app.secret_key = 'quiet_gardeners'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TreeGuardian.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    admin = User(first_name = "Preston",
                 last_name = "De Sousa",
                 username = "Preston",
                 role = "admin",
                 dob=date(2004,10,4),
                 hash_password=generate_password_hash("Preston123"),
                 is_active=False)

    existing_admin = User.query.filter_by(username="Preston").first()

    if not existing_admin:
        db.session.add(admin)
        db.session.commit()
        print("Admin created!")


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

        if not first_name and not last_name and not password and not username and not dob:
            flash("All fields are required!")

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



            if existing_user:
                flash(f"Username  {username} already exist", "danger")

            else:

                hashed_password = generate_password_hash(password)

                register_user = User(first_name=first_name,
                                     last_name=last_name,
                                     username=username,
                                     role='user',
                                     dob=datetime.strptime(dob, "%Y-%m-%d").date(),
                                     hash_password=hashed_password,
                                     is_active=False)

                db.session.add(register_user)
                db.session.commit()


                flash("registration successful !", "success")
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

    return render_template("homepage.html", username=session['username'], role=session.get('role', 'user'))

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

