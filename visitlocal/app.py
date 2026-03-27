from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "secret_key"

# Connexion DB
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# ======================
# ROUTES PRINCIPALES
# ======================

@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM activites LIMIT 3")
    activites = cursor.fetchall()

    conn.close()

    return render_template('index.html', activites=activites)

@app.route('/activites')
def activites():
    recherche = request.args.get('recherche', '').strip()
    categorie = request.args.get('categorie', '').strip()
    tri = request.args.get('tri', '').strip()

    conn = get_db_connection()

    query = "SELECT * FROM activites WHERE 1=1"
    params = []

    if recherche:
        query += " AND (titre LIKE ? OR lieu LIKE ? OR description LIKE ?)"
        search_value = f"%{recherche}%"
        params.extend([search_value, search_value, search_value])

    if categorie:
        query += " AND categorie = ?"
        params.append(categorie)

    if tri == 'prix_asc':
        query += " ORDER BY prix ASC"
    elif tri == 'prix_desc':
        query += " ORDER BY prix DESC"
    elif tri == 'date_asc':
        query += " ORDER BY date_activite ASC"
    elif tri == 'date_desc':
        query += " ORDER BY date_activite DESC"
    else:
        query += " ORDER BY id DESC"

    activites = conn.execute(query, params).fetchall()

    categories = conn.execute(
        "SELECT DISTINCT categorie FROM activites ORDER BY categorie ASC"
    ).fetchall()

    conn.close()

    return render_template(
        'activites.html',
        activites=activites,
        categories=categories,
        recherche=recherche,
        categorie_active=categorie,
        tri_actif=tri
    )
    
@app.route('/activite/<int:id>')
def activite_detail(id):
    conn = get_db_connection()

    activite = conn.execute(
        'SELECT * FROM activites WHERE id = ?',
        (id,)
    ).fetchone()

    if activite is None:
        conn.close()
        return "Activité introuvable"

    avis = conn.execute(
        '''
        SELECT avis.*, users.nom
        FROM avis
        JOIN users ON avis.user_id = users.id
        WHERE avis.activite_id = ?
        ORDER BY avis.date_avis DESC
        ''',
        (id,)
    ).fetchall()

    conn.close()

    return render_template('activite_detail.html', activite=activite, avis=avis)
    
@app.route('/favori/<int:activite_id>')
def ajouter_favori(activite_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    deja = conn.execute(
        'SELECT * FROM favoris WHERE user_id = ? AND activite_id = ?',
        (session['user_id'], activite_id)
    ).fetchone()

    if not deja:
        conn.execute(
            'INSERT INTO favoris (user_id, activite_id) VALUES (?, ?)',
            (session['user_id'], activite_id)
        )
        conn.commit()
        flash("Activité ajoutée aux favoris.", "success")
    else:
        flash("Cette activité est déjà dans vos favoris.", "warning")

    conn.close()
    return redirect('/activites')


@app.route('/favoris')
def favoris():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    favoris = conn.execute(
        '''
        SELECT activites.*
        FROM favoris
        JOIN activites ON favoris.activite_id = activites.id
        WHERE favoris.user_id = ?
        ORDER BY favoris.id DESC
        ''',
        (session['user_id'],)
    ).fetchall()

    conn.close()

    return render_template('favoris.html', favoris=favoris)


@app.route('/favori/supprimer/<int:activite_id>', methods=['POST'])
def supprimer_favori(activite_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    conn.execute(
        'DELETE FROM favoris WHERE user_id = ? AND activite_id = ?',
        (session['user_id'], activite_id)
    )
    conn.commit()
    conn.close()

    flash("Activité retirée des favoris.", "success")
    return redirect('/favoris')
    
@app.route('/profil', methods=['GET', 'POST'])
def profil():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    user = conn.execute(
        'SELECT * FROM users WHERE id = ?',
        (session['user_id'],)
    ).fetchone()

    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        nouveau_mdp = request.form['mot_de_passe']

        if nouveau_mdp.strip():
            mot_de_passe_hash = generate_password_hash(nouveau_mdp)
            conn.execute(
                'UPDATE users SET nom = ?, email = ?, mot_de_passe = ? WHERE id = ?',
                (nom, email, mot_de_passe_hash, session['user_id'])
            )
        else:
            conn.execute(
                'UPDATE users SET nom = ?, email = ? WHERE id = ?',
                (nom, email, session['user_id'])
            )

        conn.commit()

        session['user_name'] = nom
        flash("Profil mis à jour avec succès.", "success")

        user = conn.execute(
            'SELECT * FROM users WHERE id = ?',
            (session['user_id'],)
        ).fetchone()

    conn.close()

    return render_template('profil.html', user=user)
    
@app.route('/avis/ajouter/<int:activite_id>', methods=['POST'])
def ajouter_avis(activite_id):
    if 'user_id' not in session:
        return redirect('/login')

    note = request.form['note']
    commentaire = request.form['commentaire']

    conn = get_db_connection()

    conn.execute(
        '''
        INSERT INTO avis (user_id, activite_id, note, commentaire, date_avis)
        VALUES (?, ?, ?, ?, ?)
        ''',
        (
            session['user_id'],
            activite_id,
            note,
            commentaire,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
    )

    conn.commit()
    conn.close()

    flash("Votre avis a bien été ajouté.", "success")
    return redirect(f'/activite/{activite_id}')

# ======================
# AUTHENTIFICATION
# ======================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (nom, email, mot_de_passe) VALUES (?, ?, ?)',
                (nom, email, password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Email déjà utilisé"

        conn.close()
        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['mot_de_passe'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['nom']
            session['role'] = user['role']
            return redirect('/')
        else:
            return "Identifiants incorrects"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ======================
# RÉSERVATION
# ======================

@app.route('/reserver/<int:activite_id>', methods=['POST'])
def reserver(activite_id):
    if 'user_id' not in session:
        return redirect('/login')

    try:
        nb_places = int(request.form['nb_places'])
    except:
        flash("Erreur dans le formulaire.", "danger")
        return redirect('/activites')

    conn = get_db_connection()
    activite = conn.execute(
        'SELECT * FROM activites WHERE id = ?',
        (activite_id,)
    ).fetchone()

    if activite is None:
        conn.close()
        return "Activité introuvable"

    if nb_places <= 0:
        conn.close()
        flash("Nombre de places invalide.", "danger")
        return redirect('/activites')

    if nb_places > activite['places_disponibles']:
        conn.close()
        flash("Pas assez de places disponibles.", "danger")
        return redirect('/activites')

    # insertion réservation
    conn.execute(
        'INSERT INTO reservations (user_id, activite_id, nb_places, date_reservation) VALUES (?, ?, ?, ?)',
        (session['user_id'], activite_id, nb_places, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )

    # mise à jour places
    conn.execute(
        'UPDATE activites SET places_disponibles = ? WHERE id = ?',
        (activite['places_disponibles'] - nb_places, activite_id)
    )

    conn.commit()
    conn.close()
    
    flash("Votre résérvation a bien été pris en compte.", "success")
    return redirect('/mes_reservations')

@app.route('/mes_reservations')
def mes_reservations():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    reservations = conn.execute('''
    		SELECT reservations.id, reservations.nb_places, reservations.date_reservation, reservations.statut,
           		activites.titre, activites.lieu, activites.date_activite, activites.prix
    		FROM reservations
    		JOIN activites ON reservations.activite_id = activites.id
    		WHERE reservations.user_id = ?
    		ORDER BY reservations.date_reservation DESC
	''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('mes_reservations.html', reservations=reservations)
# ======================
# ADMIN
# ======================

def is_admin():
    return session.get('role') == 'admin'

@app.route('/admin')
def admin_dashboard():
    if not is_admin():
        return "Accès refusé"
    return render_template('admin_dashboard.html')

@app.route('/admin/activites')
def admin_activites():
    if not is_admin():
        return "Accès refusé"

    conn = get_db_connection()
    activites = conn.execute('SELECT * FROM activites').fetchall()
    conn.close()

    return render_template('admin_activites.html', activites=activites)

@app.route('/admin/activites/ajouter', methods=['GET', 'POST'])
def ajouter_activite():
    if not is_admin():
        return "Accès refusé"

    if request.method == 'POST':
        titre = request.form['titre']
        description = request.form['description']
        lieu = request.form['lieu']
        date = request.form['date']
        prix = request.form['prix']
        places = request.form['places']
        categorie = request.form['categorie']

        image_file = request.files.get('image')
        image_filename = None

        if image_file and image_file.filename != "":
            filename = secure_filename(image_file.filename)
            image_path = os.path.join('static/images', filename)
            image_file.save(image_path)
            image_filename = filename

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO activites (titre, description, lieu, date_activite, prix, places_disponibles, categorie, image)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (titre, description, lieu, date, prix, places, categorie, image_filename))

        conn.commit()
        conn.close()

        return redirect('/admin/activites')

    return render_template('admin_ajout_activite.html')
    
@app.route('/admin/activites/modifier/<int:id>', methods=['GET', 'POST'])
def modifier_activite(id):
    if not is_admin():
        return "Accès refusé"

    conn = get_db_connection()
    activite = conn.execute(
        'SELECT * FROM activites WHERE id = ?',
        (id,)
    ).fetchone()

    if activite is None:
        conn.close()
        return "Activité introuvable"

    if request.method == 'POST':
        titre = request.form['titre']
        description = request.form['description']
        lieu = request.form['lieu']
        date = request.form['date']
        prix = request.form['prix']
        places = request.form['places']
        categorie = request.form['categorie']

        conn.execute(
            '''
            UPDATE activites
            SET titre = ?, description = ?, lieu = ?, date_activite = ?, prix = ?, places_disponibles = ?, categorie = ?
            WHERE id = ?
            ''',
            (titre, description, lieu, date, prix, places, categorie, id)
        )

        conn.commit()
        conn.close()

        return redirect('/admin/activites')

    conn.close()
    return render_template('admin_modifier_activite.html', activite=activite)
    
@app.route('/admin/activites/supprimer/<int:id>')
def supprimer_activite(id):
    if not is_admin():
        return "Accès refusé"

    conn = get_db_connection()
    conn.execute('DELETE FROM activites WHERE id = ?', (id,))
    conn.commit()
    conn.close()

    return redirect('/admin/activites')
    
@app.route('/annuler_reservation/<int:reservation_id>', methods=['POST'])
def annuler_reservation(reservation_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()

    reservation = conn.execute(
        'SELECT * FROM reservations WHERE id = ? AND user_id = ?',
        (reservation_id, session['user_id'])
    ).fetchone()

    if reservation is None:
        conn.close()
        flash("Réservation introuvable.", "danger")
        return redirect('/mes_reservations')

    if reservation['statut'] == 'annulée':
        conn.close()
        flash("Cette réservation est déjà annulée.", "warning")
        return redirect('/mes_reservations')

    conn.execute(
        'UPDATE activites SET places_disponibles = places_disponibles + ? WHERE id = ?',
        (reservation['nb_places'], reservation['activite_id'])
    )

    conn.execute(
        'UPDATE reservations SET statut = ? WHERE id = ?',
        ('annulée', reservation_id)
    )

    conn.commit()
    conn.close()

    flash("La réservation a bien été annulée.", "success")
    return redirect('/mes_reservations')
# ======================
# LANCEMENT
# ======================

if __name__ == '__main__':
    app.run(debug=True)
