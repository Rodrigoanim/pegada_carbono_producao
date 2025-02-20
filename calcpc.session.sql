-- Primeiro, vamos dropar a tabela atual se ela existir
-- DROP TABLE IF EXISTS forms_result_sea;

-- Agora, vamos criar a tabela com a estrutura exata da forms_resultados
CREATE TABLE forms_energetica (
    ID_element INTEGER PRIMARY KEY,
    name_element TEXT NOT NULL,
    type_element TEXT NOT NULL,
    math_element TEXT,
    msg_element TEXT,
    value_element REAL,
    select_element TEXT,
    str_element TEXT,
    e_col INTEGER,
    e_row INTEGER,
    user_id INTEGER,
    section TEXT
);

-- E inserir os dados da forms_resultados
INSERT INTO forms_energetica 
SELECT * FROM forms_setorial;
