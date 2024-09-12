from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta
import random
import os
import json
import boto3

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aalo_labs_org.db'
#app.static_folder='./static/'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'  # Change this to a random secret key
db = SQLAlchemy(app)
migrate = Migrate(app, db)
s3_client = boto3.client('s3', region_name='eu-north-1', aws_access_key_id="", 
                         aws_secret_access_key="")

# Models
class Organization(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='organization', lazy=True)

class Project(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    org_id = db.Column(db.String(36), db.ForeignKey('organization.id'), nullable=False)
    applications = db.relationship('Application', backref='project', lazy=True)

class Application(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.String(36), db.ForeignKey('project.id'), nullable=False)
    api_keys = db.relationship('APIKey', backref='application', lazy=True)

class APIKey(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    application_id = db.Column(db.String(36), db.ForeignKey('application.id'), nullable=False)
    usages = db.relationship('APIKeyUsage', backref='api_key', lazy=True)

class APIKeyUsage(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    api_key_id = db.Column(db.String(36), db.ForeignKey('api_key.id'), nullable=False)

# Routes
@app.route('/')
def index():
    if 'org_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    name = data.get('org_name')
    email = data.get('email')
    password = data.get('password')

    if not name or not email or not password:
        return jsonify({"error": "All fields are required"}), 400

    existing_org = Organization.query.filter_by(email=email).first()
    if existing_org:
        return jsonify({"error": "Email already registered"}), 400

    hashed_password = generate_password_hash(password)
    new_org = Organization(name=name, email=email, password_hash=hashed_password)
    
    try:
        db.session.add(new_org)
        db.session.commit()
        return jsonify({"message": "Organization registered successfully"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "An error occurred during registration"}), 500

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    org = Organization.query.filter_by(email=email).first()
    if org and check_password_hash(org.password_hash, password):
        session['org_id'] = org.id
        return jsonify({"message": "Logged in successfully"}), 200
    return jsonify({"error": "Invalid email or password"}), 401

@app.route('/api/logout')
def logout():
    session.pop('org_id', None)
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'org_id' not in session:
        return redirect(url_for('index'))
    org = Organization.query.get(session['org_id'])
    return render_template('dashboard.html', org=org)

@app.route('/api/get_projects')
def get_projects():
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    projects = Project.query.filter_by(org_id=session['org_id']).all()
    return jsonify([{"id": p.id, "name": p.name, "description": p.description} for p in projects])

@app.route('/api/get_project/<string:project_id>')
def get_project(project_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    project = Project.query.filter_by(id=project_id, org_id=session['org_id']).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({"id": project.id, "name": project.name, "description": project.description})

@app.route('/api/get_applications/<string:project_id>')
def get_applications(project_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    project = Project.query.filter_by(id=project_id, org_id=session['org_id']).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    applications = Application.query.filter_by(project_id=project_id).all()
    return jsonify([{"id": a.id, "name": a.name, "description": a.description} for a in applications])

@app.route('/api/create_project', methods=['POST'])
def create_project():
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({"error": "Project name is required"}), 400

    new_project = Project(name=name, description=description, org_id=session['org_id'])
    db.session.add(new_project)
    db.session.commit()

    return jsonify({"message": "Project created successfully", "project_id": new_project.id}), 201

@app.route('/api/create_application', methods=['POST'])
def create_application():
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    project_id = data.get('project_id')
    name = data.get('name')
    description = data.get('description')

    print(data)

    if not project_id or not name:
        return jsonify({"error": "Project ID and application name are required"}), 400

    project = Project.query.filter_by(id=project_id, org_id=session['org_id']).first()
    if not project:
        return jsonify({"error": "Invalid project ID"}), 400

    new_app = Application(name=name, description=description, project_id=project_id)
    db.session.add(new_app)
    db.session.commit()

    # Create an initial API key for the new application
    api_key_response = create_api_key(new_app.id)
    api_key_data = json.loads(api_key_response[0].get_data(as_text=True))
    api_key = api_key_data.get('api_key')

    return jsonify({
        "message": "Application created successfully",
        "application_id": str(new_app.id),
        "api_key": api_key
    }), 201


from flask import Flask, jsonify, redirect, session, url_for, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cognito_lib import CognitoAuth
from flask_cognito_lib.decorators import auth_required, cognito_login, cognito_login_callback, cognito_logout
import boto3
import uuid
from datetime import datetime, timedelta
import random
import os
import json
from urllib.parse import quote_plus


app = Flask(__name__)

# Configuration for AWS Cognito
app.config["AWS_REGION"] = "eu-north-1"
app.config["AWS_COGNITO_USER_POOL_ID"] = "eu-north-1_xGAaQ8aax"
app.config["AWS_COGNITO_DOMAIN"] = "https://aaluv1.auth.eu-north-1.amazoncognito.com"
app.config["AWS_COGNITO_USER_POOL_CLIENT_ID"] = "a7bu12m5cdrg3j07d94emfqlj"
app.config["AWS_COGNITO_USER_POOL_CLIENT_SECRET"] = "1f21fr276erbrh57ddtlf3ogin4dc6nn6cn443ei6si482vkd9li"
app.config["AWS_COGNITO_REDIRECT_URL"] = "https://16.16.119.12/postlogin"
app.config["AWS_COGNITO_LOGOUT_URL"] = "https://16.16.119.12/postlogout"
app.config["AWS_COGNITO_REFRESH_FLOW_ENABLED"] = True
app.config["AWS_COGNITO_REFRESH_COOKIE_ENCRYPTED"] = True
app.config["AWS_COGNITO_REFRESH_COOKIE_AGE_SECONDS"] = 86400

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aalo_labs_org.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key_here'

db = SQLAlchemy(app)
migrate = Migrate(app, db)
auth = CognitoAuth(app)

s3_client = boto3.client('s3', region_name='eu-north-1', aws_access_key_id="", 
                         aws_secret_access_key="")

# Models
class Organization(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='organization', lazy=True)
    password_hash = db.Column(db.String(128), nullable=True)

class Project(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    org_id = db.Column(db.String(36), db.ForeignKey('organization.id'), nullable=False)
    applications = db.relationship('Application', backref='project', lazy=True)

class Application(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.String(36), db.ForeignKey('project.id'), nullable=False)
    api_keys = db.relationship('APIKey', backref='application', lazy=True)

class APIKey(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    application_id = db.Column(db.String(36), db.ForeignKey('application.id'), nullable=False)
    usages = db.relationship('APIKeyUsage', backref='api_key', lazy=True)

class APIKeyUsage(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    api_key_id = db.Column(db.String(36), db.ForeignKey('api_key.id'), nullable=False)

# Routes
    
def get_sign_out_url():
    cognito_domain = app.config["AWS_COGNITO_DOMAIN"]
    client_id = app.config["AWS_COGNITO_USER_POOL_CLIENT_ID"]
    logout_uri = quote_plus(app.config["AWS_COGNITO_LOGOUT_URL"])
    
    return f"{cognito_domain}/logout?client_id={client_id}&logout_uri={logout_uri}"
# Add this method to the CognitoAuth class
CognitoAuth.get_sign_out_url = get_sign_out_url
@app.route('/')
def index():
    return render_template('index.html')

@app.route("/login")
@cognito_login
def login():
    pass

@app.route("/register")
@cognito_login
def register():
    pass

@app.route("/postlogin")
@cognito_login_callback
def postlogin():
    return redirect(url_for("dashboard"))

@app.route("/logout")
@auth_required()
def logout():
    logout_url = get_sign_out_url()
    cognito_logout(lambda: None)()
    session.clear()
    return redirect(logout_url)

@app.route("/postlogout")
def postlogout():
    session.clear()
    return redirect(url_for("index"))

@app.route('/dashboard')
@auth_required()
def dashboard():
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return redirect(url_for('create_organization'))
    return render_template('dashboard.html', org=org)

@app.route('/create_organization', methods=['GET', 'POST'])
@auth_required()
def create_organization():
    if request.method == 'POST':
        name = request.form.get('name')
        email = session['user_info']['email']
        org = Organization(name=name, email=email)
        db.session.add(org)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('create_organization.html')

@app.route('/api/get_projects')
@auth_required()
def get_projects():
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    projects = Project.query.filter_by(org_id=org.id).all()
    return jsonify([{"id": p.id, "name": p.name, "description": p.description} for p in projects])


@app.route('/api/get_project/<string:project_id>')
@auth_required()
def get_project(project_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    project = Project.query.filter_by(id=project_id, org_id=org.id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    return jsonify({
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "created_at": project.created_at.isoformat()
    })
@app.route('/api/create_project', methods=['POST'])
@auth_required()
def create_project():
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.json
    name = data.get('name')
    description = data.get('description')

    if not name:
        return jsonify({"error": "Project name is required"}), 400

    new_project = Project(name=name, description=description, org_id=org.id)
    db.session.add(new_project)
    db.session.commit()

    return jsonify({"message": "Project created successfully", "project_id": new_project.id}), 201

@app.route('/api/get_applications/<string:project_id>')
@auth_required()
def get_applications(project_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    project = Project.query.filter_by(id=project_id, org_id=org.id).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    applications = Application.query.filter_by(project_id=project_id).all()
    return jsonify([{"id": a.id, "name": a.name, "description": a.description} for a in applications])


@app.route('/api/get_application/<string:app_id>')
@auth_required()
def get_application(app_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == org.id
    ).first()

    if not application:
        return jsonify({"error": "Application not found"}), 404

    return jsonify({
        "id": application.id,
        "name": application.name,
        "description": application.description,
        "created_at": application.created_at.isoformat(),
        "project_id": application.project_id
    })
@app.route('/api/create_application', methods=['POST'])
@auth_required()
def create_application():
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404
    
    data = request.json
    project_id = data.get('project_id')
    name = data.get('name')
    description = data.get('description')

    if not project_id or not name:
        return jsonify({"error": "Project ID and application name are required"}), 400

    project = Project.query.filter_by(id=project_id, org_id=org.id).first()
    if not project:
        return jsonify({"error": "Invalid project ID"}), 400

    new_app = Application(name=name, description=description, project_id=project_id)
    db.session.add(new_app)
    db.session.commit()

    api_key = str(uuid.uuid4())
    new_key = APIKey(key=api_key, application_id=new_app.id)
    db.session.add(new_key)
    db.session.commit()

    return jsonify({
        "message": "Application created successfully",
        "application_id": str(new_app.id),
        "api_key": api_key
    }), 201

@app.route('/api/get_api_keys/<string:app_id>')
@auth_required()
def get_api_keys(app_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == org.id
    ).first()

    if not application:
        return jsonify({"error": "Application not found"}), 404

    api_keys = APIKey.query.filter_by(application_id=app_id).all()
    return jsonify([{
        "id": key.id,
        "key": key.key,
        "created_at": key.created_at.isoformat(),
        "last_used": key.last_used.isoformat() if key.last_used else None,
        "is_active": key.is_active
    } for key in api_keys])

@app.route('/api/create_api_key/<string:app_id>', methods=['POST'])
@auth_required()
def create_api_key(app_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == org.id
    ).first()

    if not application:
        return jsonify({"error": "Invalid application ID"}), 400

    key = str(uuid.uuid4())
    new_key = APIKey(key=key, application_id=app_id)
    db.session.add(new_key)
    db.session.commit()

    return jsonify({"api_key": key}), 201

@app.route('/api/revoke_api_key/<string:key_id>', methods=['POST'])
@auth_required()
def revoke_api_key(key_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    api_key = APIKey.query.join(Application).join(Project).join(Organization).filter(
        APIKey.id == key_id,
        Organization.id == org.id
    ).first()

    if not api_key:
        return jsonify({"error": "Invalid API key ID"}), 400

    api_key.is_active = False
    db.session.commit()

    return jsonify({"message": "API key revoked successfully"}), 200

@app.route('/api/authenticate_key', methods=['POST'])
def authenticate_key():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Bearer token is required"}), 400

    api_key = auth_header.split(' ')[1]

    key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()

    if not key_record:
        return jsonify({"error": "Invalid or inactive API key"}), 401

    key_record.last_used = datetime.utcnow()
    db.session.commit()

    application = key_record.application
    project = application.project
    organization = project.organization

    return jsonify({
        "message": "API key authenticated successfully",
        "organization_id": organization.id,
        "organization_name": organization.name,
        "project_id": project.id,
        "project_name": project.name,
        "application_id": application.id,
        "application_name": application.name
    }), 200

@app.route('/api/get_dashboard_data')
@auth_required()
def get_dashboard_data():
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    total_requests = random.randint(10000, 100000)
    requests_this_month = random.randint(1000, 10000)

    usage_data = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        requests = random.randint(100, 1000)
        usage_data.append({"date": date, "requests": requests})
    usage_data.reverse()

    return jsonify({
        "total_requests": total_requests,
        "requests_this_month": requests_this_month,
        "usage_data": usage_data,
        "current_plan": "Professional",
        "next_billing_date": (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
        "current_usage": random.uniform(50, 200),
        "total_projects": Project.query.filter_by(org_id=org.id).count(),
        "total_applications": Application.query.join(Project).filter(Project.org_id == org.id).count(),
        "active_api_keys": APIKey.query.join(Application).join(Project).filter(Project.org_id == org.id, APIKey.is_active == True).count(),
        "recent_activity": [
            "New API key created for Project X",
            "Project Y reached 10,000 requests",
            "New application 'Z' added to Project X",
            "Billing information updated"
        ]
    })

@app.route('/api/store_json', methods=['POST'])
def store_json():
    data = request.json['data']
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Bearer token is required"}), 400

    api_key = auth_header.split(' ')[1]

    key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()

    if not key_record:
        return jsonify({"error": "Invalid or inactive API key"}), 401

    application = key_record.application
    project = application.project
    organization = project.organization

    base_path = os.path.join(organization.id, project.id, application.id, request.json['runID'])

    filename = f"{uuid.uuid4()}.json"
    file_path = os.path.join(base_path, filename)

    json_string = json.dumps(data)
    s3_client.put_object(Bucket='aalubucket', Key=file_path, Body=json_string)

    return jsonify({
        "message": "JSON data stored successfully",
        "file_path": file_path
    }), 200

@app.route('/api/get_json_files/<string:app_id>')
@auth_required()
def get_json_files(app_id):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == org.id
    ).first()

    if not application:
        return jsonify({"error": "Application not found"}), 404

    prefix = f"{org.id}/{application.project.id}/{app_id}/"
    print(prefix)

    try:
        response = s3_client.list_objects_v2(Bucket='aalubucket', Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]
        return jsonify(files), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_json_content/<path:file_path>')
@auth_required()
def get_json_content(file_path):
    user_email = session['user_info']['email']
    org = Organization.query.filter_by(email=user_email).first()
    if not org:
        return jsonify({"error": "Organization not found"}), 404

    try:
        response = s3_client.get_object(Bucket='aalubucket', Key=file_path)
        content = response['Body'].read().decode('utf-8')
        return jsonify(json.loads(content)), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, ssl_context=('cert.pem', 'key.pem'))

@app.route('/api/revoke_api_key/<string:key_id>', methods=['POST'])
def revoke_api_key(key_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    api_key = APIKey.query.join(Application).join(Project).join(Organization).filter(
        APIKey.id == key_id,
        Organization.id == session['org_id']
    ).first()

    if not api_key:
        return jsonify({"error": "Invalid API key ID"}), 400

    api_key.is_active = False
    db.session.commit()

    return jsonify({"message": "API key revoked successfully"}), 200

@app.route('/api/get_api_keys/<string:app_id>')
def get_api_keys(app_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == session['org_id']
    ).first()

    if not application:
        return jsonify({"error": "Application not found"}), 404

    api_keys = APIKey.query.filter_by(application_id=app_id).all()
    return jsonify([{
        "id": key.id,
        "key": key.key,
        "created_at": key.created_at.isoformat(),
        "last_used": key.last_used.isoformat() if key.last_used else None,
        "is_active": key.is_active
    } for key in api_keys])

@app.route('/api/create_api_key/<string:app_id>', methods=['POST'])
def create_api_key(app_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == session['org_id']
    ).first()

    if not application:
        return jsonify({"error": "Invalid application ID"}), 400

    key = str(uuid.uuid4())
    print(key)
    new_key = APIKey(key=key, application_id=app_id)
    db.session.add(new_key)
    db.session.commit()

    return jsonify({"api_key": key}), 201

@app.route('/api/get_api_key_usage/<string:key_id>')
def get_api_key_usage(key_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    api_key = APIKey.query.join(Application).join(Project).join(Organization).filter(
        APIKey.id == key_id,
        Organization.id == session['org_id']
    ).first()

    if not api_key:
        return jsonify({"error": "Invalid API key ID"}), 400

    # For demonstration purposes, we'll generate random usage data
    # In a real application, you would query the APIKeyUsage table
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    usage_data = []

    current_date = start_date
    while current_date <= end_date:
        usage_count = random.randint(0, 100)
        usage_data.append({
            "date": current_date.strftime("%Y-%m-%d"),
            "count": usage_count
        })
        current_date += timedelta(days=1)

    return jsonify(usage_data)

@app.route('/api/authenticate_key', methods=['POST'])
def authenticate_key():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Bearer token is required"}), 400

    api_key = auth_header.split(' ')[1]

    # Find the API key in the database
    key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()

    if not key_record:
        return jsonify({"error": "Invalid or inactive API key"}), 401

    # Update last used timestamp
    key_record.last_used = datetime.utcnow()
    db.session.commit()

    # Fetch related information
    application = key_record.application
    project = application.project
    organization = project.organization

    return jsonify({
        "message": "API key authenticated successfully",
        "organization_id": organization.id,
        "organization_name": organization.name,
        "project_id": project.id,
        "project_name": project.name,
        "application_id": application.id,
        "application_name": application.name
    }), 200

@app.route('/api/get_dashboard_data')
def get_dashboard_data():
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    org_id = session['org_id']
    
    # In a real application, you would fetch this data from your database
    # This is just example data
    total_requests = random.randint(10000, 100000)
    requests_this_month = random.randint(1000, 10000)

    # Generate some example usage data for the past 30 days
    usage_data = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        requests = random.randint(100, 1000)
        usage_data.append({"date": date, "requests": requests})
    usage_data.reverse()

    return jsonify({
        "total_requests": total_requests,
        "requests_this_month": requests_this_month,
        "usage_data": usage_data,
        "current_plan": "Professional",
        "next_billing_date": (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
        "current_usage": random.uniform(50, 200),
        "total_projects": Project.query.filter_by(org_id=org_id).count(),
        "total_applications": Application.query.join(Project).filter(Project.org_id == org_id).count(),
        "active_api_keys": APIKey.query.join(Application).join(Project).filter(Project.org_id == org_id, APIKey.is_active == True).count(),
        "recent_activity": [
            "New API key created for Project X",
            "Project Y reached 10,000 requests",
            "New application 'Z' added to Project X",
            "Billing information updated"
        ]
    })

def write_to_s3_with_path_creation(bucket_name, file_path, data, s3_client=None):
    if not s3_client:
        s3_client = boto3.client('s3') 
    
    directory_path = '/'.join(file_path.split('/')[:-1]) 
    
    json_string = json.dumps(data) 
    
    s3_client.put_object(Bucket=bucket_name, Key=file_path, Body=json_string)

@app.route('/api/store_json', methods=['POST'])
def store_json():
    data = request.json['data']
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Bearer token is required"}), 400

    api_key = auth_header.split(' ')[1]

    key_record = APIKey.query.filter_by(key=api_key, is_active=True).first()

    if not key_record:
        return jsonify({"error": "Invalid or inactive API key"}), 401

    application = key_record.application
    project = application.project
    organization = project.organization

    base_path = os.path.join(organization.id, project.id, application.id, request.json['runID'])

    filename = f"{uuid.uuid4()}.json"
    file_path = os.path.join(base_path, filename)

    write_to_s3_with_path_creation('aalubucket', file_path, data, s3_client)

    return jsonify({
        "message": "JSON data stored successfully",
        "file_path": file_path
    }), 200

@app.route('/api/delete_api_key/<string:key_id>', methods=['POST'])
def delete_api_key(key_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    api_key = APIKey.query.join(Application).join(Project).join(Organization).filter(
        APIKey.id == key_id,
        Organization.id == session['org_id']
    ).first()

    if not api_key:
        return jsonify({"error": "Invalid API key ID"}), 400

    try:
        db.session.delete(api_key)
        db.session.commit()
        return jsonify({"message": "API key deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"An error occurred while deleting the API key: {str(e)}"}), 500



import boto3
from botocore.exceptions import ClientError

@app.route('/api/get_json_files/<string:app_id>')
def get_json_files(app_id):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    application = Application.query.join(Project).join(Organization).filter(
        Application.id == app_id,
        Organization.id == session['org_id']
    ).first()

    if not application:
        return jsonify({"error": "Application not found"}), 404

    org_id = application.project.organization.id
    project_id = application.project.id

    prefix = f"{org_id}/{project_id}/{app_id}/"

    try:
        response = s3_client.list_objects_v2(Bucket='aalubucket', Prefix=prefix)
        files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('.json')]
        return jsonify(files), 200
    except ClientError as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get_json_content/<path:file_path>')
def get_json_content(file_path):
    if 'org_id' not in session:
        return jsonify({"error": "Not logged in"}), 401

    try:
        response = s3_client.get_object(Bucket='aalubucket', Key=file_path)
        content = response['Body'].read().decode('utf-8')
        return jsonify(json.loads(content)), 200
    except ClientError as e:
        return jsonify({"error": str(e)}), 500
    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
