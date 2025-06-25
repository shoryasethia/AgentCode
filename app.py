from flask import Flask, render_template, redirect, url_for, session, g
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY")
if not app.secret_key:
    print("Warning: SECRET_KEY not set in environment variables. Using default key for development purposes.")
    app.secret_key = "shoryasupersecretkey"

# Database Configuration
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("Warning: DATABASE_URL not set in environment variables. Exiting application.")
    exit(1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# OAuth Configuration
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

github = oauth.register(
    name='github',
    client_id=os.environ.get('GITHUB_CLIENT_ID'),
    client_secret=os.environ.get('GITHUB_CLIENT_SECRET'),
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email read:user'},
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_user_id = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=False, nullable=True)
    picture = db.Column(db.String(200))
    __table_args__ = (db.UniqueConstraint('provider', 'provider_user_id', name='_provider_user_uc'),)

@app.before_request
def load_logged_in_user():
    user_id = session.get('user_db_id')
    if user_id is None:
        g.user = None
    else:
        g.user = db.session.get(User, user_id)
        if g.user:
            session['user'] = {
                'provider': g.user.provider,
                'name': g.user.name,
                'email': g.user.email,
                'picture': g.user.picture
            }
        else:
            session.pop('user_db_id', None)
            session.pop('user', None)
            g.user = None

@app.route("/")
def entry_point():
    return redirect(url_for('auth_page'))

@app.route("/home")
def app_home():
    if not g.user:
        return redirect(url_for('auth_page'))
    return render_template("index.html", user_session_data=session.get('user'))

@app.route("/auth")
def auth_page():
    return render_template("auth.html", user_session_data=session.get('user'))

@app.route("/login/<provider_name>")
def login(provider_name):
    client = oauth.create_client(provider_name)
    if not client:
        app.logger.error(f"Attempted login with invalid provider: {provider_name}")
        return "Invalid provider", 404
    redirect_uri = url_for('auth_callback', provider_name=provider_name, _external=True)
    return client.authorize_redirect(redirect_uri)

@app.route("/auth/callback/<provider_name>")
def auth_callback(provider_name):
    client = oauth.create_client(provider_name)
    if not client:
        app.logger.error(f"Callback with invalid provider: {provider_name}")
        return "Invalid provider", 404
    
    user_data = None
    try:
        client.authorize_access_token()
        if provider_name == "google":
            user_data = client.userinfo()
        elif provider_name == "github":
            resp = client.get("user") 
            resp.raise_for_status()
            user_data = resp.json()
    except Exception as e:
        app.logger.error(f"Error in OAuth callback for {provider_name}: {e}")
        return redirect(url_for('auth_page'))

    if not user_data:
        app.logger.error(f"No user_data received from {provider_name}")
        return redirect(url_for('auth_page'))

    provider_user_id_val = None
    if provider_name == "google":
        provider_user_id_val = user_data.get("sub")
        name = user_data.get("name")
        email = user_data.get("email")
        picture = user_data.get("picture")
    elif provider_name == "github":
        provider_user_id_val = str(user_data.get("id"))
        name = user_data.get("name") or user_data.get("login")
        email = user_data.get("email")
        picture = user_data.get("avatar_url")

    if not provider_user_id_val:
        app.logger.error(f"Could not extract provider_user_id for {provider_name}")
        return redirect(url_for('auth_page'))

    user = User.query.filter_by(provider=provider_name, provider_user_id=provider_user_id_val).first()
    if user:
        user.name = name
        user.email = email
        user.picture = picture
    else:
        user = User(
            provider=provider_name,
            provider_user_id=provider_user_id_val,
            name=name,
            email=email,
            picture=picture
        )
        db.session.add(user)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Database commit failed in auth_callback: {e}")
        return redirect(url_for('auth_page'))

    if user and user.id:
        session['user_db_id'] = user.id
        session['user'] = {
            'provider': user.provider,
            'name': user.name,
            'email': user.email,
            'picture': user.picture
        }
    else:
        app.logger.error(f"User object or user.id invalid after DB operations for {provider_name}")
        return redirect(url_for('auth_page'))
    return redirect(url_for('app_home'))

@app.route("/logout")
def logout():
    session.pop('user_db_id', None) 
    session.pop('user', None)       
    g.user = None                 
    return redirect(url_for('auth_page')) # After logout, send to auth page

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    
    app.run(debug=True, port=5000, host="0.0.0.0")