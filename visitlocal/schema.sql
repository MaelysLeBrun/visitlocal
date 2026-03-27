DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS activites;
DROP TABLE IF EXISTS reservations;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    mot_de_passe TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user'
);

CREATE TABLE activites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titre TEXT NOT NULL,
    description TEXT NOT NULL,
    lieu TEXT NOT NULL,
    date_activite TEXT NOT NULL,
    prix REAL NOT NULL,
    places_disponibles INTEGER NOT NULL,
    categorie TEXT NOT NULL,
    image TEXT
);

CREATE TABLE reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activite_id INTEGER NOT NULL,
    nb_places INTEGER NOT NULL,
    date_reservation TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (activite_id) REFERENCES activites(id)
);
