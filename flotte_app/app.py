from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'gestion-flotte-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flotte.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation de la base de données
db = SQLAlchemy(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'

# Chemin vers les données JSON (pour les données initiales des camions)
DATA_FILE = os.path.join(os.path.dirname(__file__), 'data', 'flotte_data.json')

# Modèles de la base de données
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Camion(db.Model):
    __tablename__ = 'camions'
    id = db.Column(db.String(50), primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    modele = db.Column(db.String(100), default='')
    chauffeur = db.Column(db.String(100), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    transactions = db.relationship('Transaction', backref='camion', lazy=True, cascade='all, delete-orphan')
    maintenances = db.relationship('Maintenance', backref='camion', lazy=True, cascade='all, delete-orphan')

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    camion_id = db.Column(db.String(50), db.ForeignKey('camions.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    categorie = db.Column(db.String(100))
    description = db.Column(db.Text)
    revenu = db.Column(db.Float, default=0)
    depense = db.Column(db.Float, default=0)
    paiement = db.Column(db.String(50), default='Espèce')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='transactions')

class Maintenance(db.Model):
    __tablename__ = 'maintenances'
    id = db.Column(db.Integer, primary_key=True)
    camion_id = db.Column(db.String(50), db.ForeignKey('camions.id'), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False)  # vidange, pneus, freins, controle_technique
    date_derniere = db.Column(db.Date, nullable=False)
    kilometrage_dernier = db.Column(db.Integer, default=0)
    periodicite_jours = db.Column(db.Integer, default=30)
    periodicite_km = db.Column(db.Integer, default=5000)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref='maintenances')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, critical
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='notifications')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    """Initialise la base de données et importe les données JSON si nécessaire"""
    db.create_all()
    
    # Créer un admin par défaut s'il n'existe pas
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            password_hash=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()
        print("Utilisateur admin créé: username='admin', password='admin123'")
    
    # Importer les données des camions depuis le JSON si la table est vide
    if not Camion.query.first():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for camion_id, camion_info in data.items():
                # Créer le camion
                camion = Camion(
                    id=camion_id, 
                    nom=camion_info['nom'],
                    modele=camion_info.get('modele', ''),
                    chauffeur=camion_info.get('chauffeur', '')
                )
                db.session.add(camion)
                
                # Créer les transactions
                for trans in camion_info.get('transactions', []):
                    date_str = trans.get('date', '')
                    # Ignorer les lignes de total ou les dates invalides
                    if not date_str or date_str == 'TOTAL':
                        continue
                    
                    # Gérer les formats de date avec ou sans heure
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                    elif 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    
                    # Essayer différents formats de date
                    try:
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    except ValueError:
                        try:
                            # Format DD/M/YYYY
                            parsed_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                        except ValueError:
                            try:
                                # Format DD/MM/YYYY
                                parsed_date = datetime.strptime(date_str, '%d/%m/%Y').date()
                            except ValueError:
                                # Si aucun format ne correspond, utiliser la date actuelle
                                print(f"Date invalide '{date_str}' pour {camion_id}, utilisation de la date actuelle")
                                parsed_date = datetime.now().date()
                    
                    transaction = Transaction(
                        camion_id=camion_id,
                        date=parsed_date,
                        categorie=trans.get('categorie', ''),
                        description=trans.get('description', ''),
                        revenu=float(trans.get('revenu', 0) or 0),
                        depense=float(trans.get('depense', 0) or 0),
                        paiement=trans.get('paiement', 'Espèce')
                    )
                    db.session.add(transaction)
                
                # Créer les maintenances
                for maint_type, maint_info in camion_info.get('maintenance', {}).items():
                    date_str = maint_info['date_derniere']
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                    elif 'T' in date_str:
                        date_str = date_str.split('T')[0]
                    
                    maintenance = Maintenance(
                        camion_id=camion_id,
                        maintenance_type=maint_type,
                        date_derniere=datetime.strptime(date_str, '%Y-%m-%d').date(),
                        kilometrage_dernier=maint_info.get('kilometrage_dernier', 0),
                        periodicite_jours=maint_info.get('periodicite_jours', 30),
                        periodicite_km=maint_info.get('periodicite_km', maint_info.get('kilometrage_interval', 5000)),
                        notes=maint_info.get('notes', '')
                    )
                    db.session.add(maintenance)
            
            db.session.commit()
            print("Données importées depuis le fichier JSON")
        except FileNotFoundError:
            print("Fichier JSON non trouvé, base de données initialisée vide")
        except Exception as e:
            print(f"Erreur lors de l'import des données: {e}")
            db.session.rollback()

def calculate_stats_from_db():
    """Calcule les statistiques globales de la flotte depuis la base de données"""
    camions = Camion.query.all()
    total_revenu = 0
    total_depense = 0
    camions_stats = []
    
    for camion in camions:
        transactions = camion.transactions
        camion_revenu = sum(t.revenu for t in transactions)
        camion_depense = sum(t.depense for t in transactions)
        camion_benefice = camion_revenu - camion_depense
        marge = (camion_benefice / camion_revenu * 100) if camion_revenu > 0 else 0
        
        total_revenu += camion_revenu
        total_depense += camion_depense
        
        camions_stats.append({
            'id': camion.id,
            'nom': camion.nom,
            'modele': camion.modele,
            'chauffeur': camion.chauffeur,
            'revenu': camion_revenu,
            'depense': camion_depense,
            'benefice': camion_benefice,
            'marge': marge,
            'transactions_count': len(transactions)
        })
    
    benefice_net = total_revenu - total_depense
    marge_moyenne = (benefice_net / total_revenu * 100) if total_revenu > 0 else 0
    
    # Trier par performance (marge)
    camions_stats.sort(key=lambda x: x['marge'], reverse=True)
    
    return {
        'total_revenu': total_revenu,
        'total_depense': total_depense,
        'benefice_net': benefice_net,
        'marge_moyenne': marge_moyenne,
        'camions_actifs': sum(1 for c in camions_stats if c['revenu'] > 0),
        'total_camions': len(camions_stats),
        'camions_stats': camions_stats
    }

def check_maintenance_alerts_from_db():
    """Vérifie les alertes de maintenance depuis la base de données"""
    alerts = []
    today = datetime.now().date()
    
    maintenances = Maintenance.query.all()
    for maint in maintenances:
        try:
            next_due = maint.date_derniere + timedelta(days=maint.periodicite_jours)
            days_remaining = (next_due - today).days
            
            # Déterminer le statut et la priorité
            if days_remaining < 0:
                status = 'retard'
                priority = 'critical'
                message = f"En retard de {abs(days_remaining)} jours"
            elif days_remaining <= 7:
                status = 'urgent'
                priority = 'high'
                message = f"Dans {days_remaining} jours"
            elif days_remaining <= 15:
                status = 'bientot'
                priority = 'medium'
                message = f"Dans {days_remaining} jours"
            else:
                status = 'ok'
                priority = 'low'
                message = f"Dans {days_remaining} jours"
            
            # N'ajouter que les alertes qui ne sont pas 'ok'
            if status != 'ok':
                alerts.append({
                    'camion_id': maint.camion_id,
                    'camion_nom': maint.camion.nom,
                    'maintenance_type': maint.maintenance_type,
                    'date_derniere': maint.date_derniere.strftime('%Y-%m-%d'),
                    'date_prochaine': next_due.strftime('%Y-%m-%d'),
                    'jours_restant': days_remaining,
                    'status': status,
                    'priority': priority,
                    'message': message,
                    'maintenance_id': maint.id
                })
        except Exception as e:
            print(f"Erreur lors de la vérification de maintenance: {e}")
    
    # Trier par priorité (critical d'abord)
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    alerts.sort(key=lambda x: priority_order.get(x['priority'], 4))
    
    return alerts

def create_notification(user_id, title, message, priority='medium'):
    """Crée une notification pour un utilisateur"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        priority=priority
    )
    db.session.add(notification)
    db.session.commit()
    return notification

@app.route('/')
@login_required
def index():
    """Page d'accueil avec le dashboard"""
    return render_template('index.html')

@app.route('/api/data')
@login_required
def get_data():
    """API pour récupérer toutes les données depuis la base de données"""
    stats = calculate_stats_from_db()
    alerts = check_maintenance_alerts_from_db()
    
    # Récupérer tous les camions avec leurs informations
    camions_data = {}
    for camion in Camion.query.all():
        transactions = [{'date': t.date.strftime('%Y-%m-%d'), 'categorie': t.categorie, 'description': t.description, 'revenu': t.revenu, 'depense': t.depense, 'paiement': t.paiement} for t in camion.transactions]
        maintenances = {m.maintenance_type: {'date_derniere': m.date_derniere.strftime('%Y-%m-%d'), 'kilometrage_dernier': m.kilometrage_dernier, 'periodicite_jours': m.periodicite_jours} for m in camion.maintenances}
        camions_data[camion.id] = {
            'nom': camion.nom, 
            'modele': camion.modele,
            'chauffeur': camion.chauffeur,
            'transactions': transactions, 
            'maintenance': maintenances
        }
    
    return jsonify({
        'data': camions_data,
        'stats': stats,
        'alerts': alerts
    })

@app.route('/api/camion/<camion_id>')
@login_required
def get_camion(camion_id):
    """API pour récupérer les données d'un camion spécifique depuis la base de données"""
    camion = Camion.query.get(camion_id)
    if not camion:
        return jsonify({'error': 'Camion non trouvé'}), 404
    
    transactions = camion.transactions
    revenu = sum(t.revenu for t in transactions)
    depense = sum(t.depense for t in transactions)
    benefice = revenu - depense
    marge = (benefice / revenu * 100) if revenu > 0 else 0
    
    # Vérifier les alertes de maintenance pour ce camion
    camion_alerts = []
    for maint in camion.maintenances:
        try:
            next_due = maint.date_derniere + timedelta(days=maint.periodicite_jours)
            days_remaining = (next_due - datetime.now().date()).days
            
            if days_remaining < 0:
                status = 'retard'
                priority = 'critical'
                message = f"En retard de {abs(days_remaining)} jours"
            elif days_remaining <= 7:
                status = 'urgent'
                priority = 'high'
                message = f"Dans {days_remaining} jours"
            elif days_remaining <= 15:
                status = 'bientot'
                priority = 'medium'
                message = f"Dans {days_remaining} jours"
            else:
                status = 'ok'
                priority = 'low'
                message = f"Dans {days_remaining} jours"
            
            if status != 'ok':
                camion_alerts.append({
                    'maintenance_type': maint.maintenance_type,
                    'date_derniere': maint.date_derniere.strftime('%Y-%m-%d'),
                    'date_prochaine': next_due.strftime('%Y-%m-%d'),
                    'jours_restant': days_remaining,
                    'status': status,
                    'priority': priority,
                    'message': message,
                    'maintenance_id': maint.id
                })
        except Exception as e:
            print(f"Erreur lors de la vérification de maintenance pour {camion_id}: {e}")
    
    trans_list = [{'id': t.id, 'date': t.date.strftime('%Y-%m-%d'), 'categorie': t.categorie, 'description': t.description, 'revenu': t.revenu, 'depense': t.depense, 'paiement': t.paiement, 'user_id': t.user_id} for t in transactions]
    maint_dict = {m.maintenance_type: {'id': m.id, 'date_derniere': m.date_derniere.strftime('%Y-%m-%d'), 'kilometrage_dernier': m.kilometrage_dernier, 'periodicite_jours': m.periodicite_jours, 'periodicite_km': m.periodicite_km, 'notes': m.notes} for m in camion.maintenances}
    
    return jsonify({
        'id': camion.id,
        'nom': camion.nom,
        'modele': camion.modele,
        'chauffeur': camion.chauffeur,
        'transactions': trans_list,
        'maintenance': maint_dict,
        'alerts': camion_alerts,
        'stats': {
            'revenu': revenu,
            'depense': depense,
            'benefice': benefice,
            'marge': marge
        }
    })

@app.route('/api/maintenance/update', methods=['POST'])
@login_required
def update_maintenance():
    """API pour mettre à jour une maintenance effectuée dans la base de données"""
    update_info = request.json
    
    maintenance_id = update_info.get('maintenance_id')
    if not maintenance_id:
        return jsonify({'error': 'ID de maintenance requis'}), 400
    
    maint = Maintenance.query.get(maintenance_id)
    if not maint:
        return jsonify({'error': 'Maintenance non trouvée'}), 404
    
    # Mettre à jour la date de dernière maintenance
    today = datetime.now().date()
    maint.date_derniere = today
    
    # Optionnel: mettre à jour le kilométrage
    if 'kilometrage' in update_info:
        maint.kilometrage_dernier = update_info['kilometrage']
    
    # Enregistrer l'utilisateur qui a fait la mise à jour
    maint.user_id = current_user.id
    
    db.session.commit()
    
    # Créer une notification
    create_notification(
        user_id=current_user.id,
        title=f'Maintenance {maint.maintenance_type} effectuée',
        message=f'La maintenance {maint.maintenance_type} du {maint.camion.nom} a été marquée comme effectuée.',
        priority='low'
    )
    
    return jsonify({
        'success': True,
        'message': f'Maintenance {maint.maintenance_type} mise à jour avec succès',
        'new_date': today.strftime('%Y-%m-%d')
    })

@app.route('/api/alerts')
@login_required
def get_alerts():
    """API pour récupérer toutes les alertes de maintenance depuis la base de données"""
    alerts = check_maintenance_alerts_from_db()
    return jsonify({'alerts': alerts})

@app.route('/api/transaction', methods=['POST'])
@login_required
def add_transaction():
    """API pour ajouter une transaction dans la base de données"""
    new_transaction = request.json
    
    camion_id = new_transaction.get('camion_id')
    camion = Camion.query.get(camion_id)
    if not camion:
        return jsonify({'error': 'Camion non trouvé'}), 404
    
    # Créer la transaction
    transaction = Transaction(
        camion_id=camion_id,
        date=datetime.strptime(new_transaction.get('date', datetime.now().strftime('%Y-%m-%d')), '%Y-%m-%d').date(),
        categorie=new_transaction.get('categorie', ''),
        description=new_transaction.get('description', ''),
        revenu=float(new_transaction.get('revenu', 0)),
        depense=float(new_transaction.get('depense', 0)),
        paiement=new_transaction.get('paiement', 'Espèce'),
        user_id=current_user.id
    )
    
    db.session.add(transaction)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'transaction': {
            'id': transaction.id,
            'date': transaction.date.strftime('%Y-%m-%d'),
            'categorie': transaction.categorie,
            'description': transaction.description,
            'revenu': transaction.revenu,
            'depense': transaction.depense,
            'paiement': transaction.paiement
        }
    })

# Routes pour la gestion des camions (ajout, modification, suppression)
@app.route('/api/camions', methods=['GET'])
@login_required
def get_camions():
    """API pour récupérer la liste de tous les camions"""
    camions = Camion.query.all()
    camions_list = []
    for camion in camions:
        transactions = camion.transactions
        revenu = sum(t.revenu for t in transactions)
        depense = sum(t.depense for t in transactions)
        camions_list.append({
            'id': camion.id,
            'nom': camion.nom,
            'modele': camion.modele,
            'chauffeur': camion.chauffeur,
            'revenu': revenu,
            'depense': depense,
            'benefice': revenu - depense,
            'created_at': camion.created_at.strftime('%Y-%m-%d') if camion.created_at else None
        })
    return jsonify({'camions': camions_list})

@app.route('/api/camions', methods=['POST'])
@login_required
def add_camion():
    """API pour ajouter un nouveau camion"""
    data = request.json
    
    nom = data.get('nom')
    if not nom:
        return jsonify({'error': 'Le nom du camion est requis'}), 400
    
    # Générer un ID unique pour le camion
    existing_ids = [c.id for c in Camion.query.all()]
    camion_num = 1
    while f'CAMION_{camion_num}' in existing_ids:
        camion_num += 1
    camion_id = f'CAMION_{camion_num}'
    
    # Vérifier si le nom existe déjà
    if Camion.query.filter_by(nom=nom).first():
        return jsonify({'error': 'Un camion avec ce nom existe déjà'}), 400
    
    camion = Camion(
        id=camion_id,
        nom=nom,
        modele=data.get('modele', ''),
        chauffeur=data.get('chauffeur', '')
    )
    
    db.session.add(camion)
    db.session.commit()
    
    # Créer les maintenances par défaut pour le nouveau camion
    maintenance_types = [
        {'type': 'vidange', 'jours': 30, 'km': 5000},
        {'type': 'pneus', 'jours': 90, 'km': 20000},
        {'type': 'freins', 'jours': 60, 'km': 15000},
        {'type': 'controle_technique', 'jours': 180, 'km': 50000}
    ]
    
    for maint in maintenance_types:
        maintenance = Maintenance(
            camion_id=camion_id,
            maintenance_type=maint['type'],
            date_derniere=datetime.now().date(),
            kilometrage_dernier=0,
            periodicite_jours=maint['jours'],
            periodicite_km=maint['km'],
            notes=f'Maintenance {maint["type"]} initialisée pour {nom}',
            user_id=current_user.id
        )
        db.session.add(maintenance)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'camion': {
            'id': camion.id,
            'nom': camion.nom,
            'modele': camion.modele,
            'chauffeur': camion.chauffeur
        }
    })

@app.route('/api/camions/<camion_id>', methods=['PUT'])
@login_required
def update_camion(camion_id):
    """API pour modifier les informations d'un camion"""
    camion = Camion.query.get(camion_id)
    if not camion:
        return jsonify({'error': 'Camion non trouvé'}), 404
    
    data = request.json
    
    # Mettre à jour les champs si fournis
    if 'nom' in data:
        # Vérifier que le nouveau nom n'existe pas déjà pour un autre camion
        existing = Camion.query.filter_by(nom=data['nom']).first()
        if existing and existing.id != camion_id:
            return jsonify({'error': 'Un camion avec ce nom existe déjà'}), 400
        camion.nom = data['nom']
    
    if 'modele' in data:
        camion.modele = data['modele']
    
    if 'chauffeur' in data:
        camion.chauffeur = data['chauffeur']
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'camion': {
            'id': camion.id,
            'nom': camion.nom,
            'modele': camion.modele,
            'chauffeur': camion.chauffeur
        }
    })

@app.route('/api/camions/<camion_id>', methods=['DELETE'])
@login_required
def delete_camion(camion_id):
    """API pour supprimer un camion"""
    camion = Camion.query.get(camion_id)
    if not camion:
        return jsonify({'error': 'Camion non trouvé'}), 404
    
    # Supprimer le camion (les transactions et maintenances seront supprimées grâce à cascade)
    db.session.delete(camion)
    db.session.commit()
    
    return jsonify({'success': True, 'message': f'Camion {camion.nom} supprimé avec succès'})
@app.route('/camion/<camion_id>')
@login_required
def camion_detail(camion_id):
    """Page de détail d'un camion"""
    return render_template('camion.html', camion_id=camion_id)

@app.route('/comparatif')
@login_required
def comparatif():
    """Page de comparatif des performances"""
    return render_template('comparatif.html')

# Routes d'authentification
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Page de connexion"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Trouver l'utilisateur
        user = None
        for u in users_db.values():
            if u.username == username:
                user = u
                break
        
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            flash('Connexion réussie!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Nom d\'utilisateur ou mot de passe incorrect', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Déconnexion"""
    logout_user()
    flash('Vous avez été déconnecté avec succès.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Page d'inscription"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Vérifications
        if not username or not password:
            flash('Veuillez remplir tous les champs', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Les mots de passe ne correspondent pas', 'error')
            return render_template('register.html')
        
        # Vérifier si l'utilisateur existe déjà
        if User.query.filter_by(username=username).first():
            flash('Ce nom d\'utilisateur est déjà pris', 'error')
            return render_template('register.html')
        
        # Créer un nouvel utilisateur dans la base de données
        new_user = User(
            username=username,
            password_hash=generate_password_hash(password),
            role='user'
        )
        db.session.add(new_user)
        db.session.commit()
        
        flash('Compte créé avec succès! Veuillez vous connecter.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """API pour récupérer la liste des utilisateurs (admin seulement)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    users_list = []
    for user in User.query.all():
        users_list.append({
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': user.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify({'users': users_list})

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    """API pour créer un nouvel utilisateur (admin seulement)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Accès non autorisé'}), 403
    
    new_user_data = request.json
    username = new_user_data.get('username')
    password = new_user_data.get('password')
    role = new_user_data.get('role', 'user')
    
    if not username or not password:
        return jsonify({'error': 'Username et password requis'}), 400
    
    # Vérifier si l'utilisateur existe déjà
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Cet utilisateur existe déjà'}), 400
    
    # Créer un nouvel utilisateur dans la base de données
    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'user': {'id': new_user.id, 'username': username, 'role': role}})

@app.route('/api/notifications')
@login_required
def get_notifications():
    """API pour récupérer les notifications de l'utilisateur"""
    unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).all()
    read = Notification.query.filter_by(user_id=current_user.id, is_read=True).order_by(Notification.created_at.desc()).limit(10).all()
    
    unread_list = [{'id': n.id, 'title': n.title, 'message': n.message, 'priority': n.priority, 'is_read': n.is_read, 'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')} for n in unread]
    read_list = [{'id': n.id, 'title': n.title, 'message': n.message, 'priority': n.priority, 'is_read': n.is_read, 'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')} for n in read]
    
    return jsonify({'unread': unread_list, 'read': read_list, 'unread_count': len(unread)})

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Marquer une notification comme lue"""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({'error': 'Notification non trouvée'}), 404
    
    notification.is_read = True
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """Marquer toutes les notifications comme lues"""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/profile')
@login_required
def profile():
    """Page de profil utilisateur"""
    return render_template('profile.html')

if __name__ == '__main__':
    # Initialiser la base de données
    with app.app_context():
        init_db()
    app.run(debug=False, host='0.0.0.0', port=5001)
