CREATE TABLE IF NOT EXISTS log_acessos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    data_acesso DATE NOT NULL,
    programa TEXT NOT NULL,
    acao TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES usuarios(user_id)
);