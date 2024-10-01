import os
import psycopg2
from dotenv import load_dotenv
from DB.start_words import start_words

load_dotenv()


def create_tables(connection):
    with conn.cursor() as cur:
        cur.execute("""
            DROP TABLE IF EXISTS users_words;
            DROP TABLE IF EXISTS users;
            DROP TABLE IF EXISTS words;
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS words(
                id SERIAL PRIMARY KEY,
                eng VARCHAR(30) NOT NULL,
                rus VARCHAR(30) NOT NULL UNIQUE);
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id SERIAL PRIMARY KEY,
                tg_id BIGINT NOT NULL UNIQUE);
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users_words(
                id_word INTEGER NOT NULL REFERENCES words(id),
                id_user INTEGER NOT NULL REFERENCES users(id),
                CONSTRAINT users_words_fk PRIMARY KEY (id_word, id_user));
        """)


def insert_start_words(connection, rus_word, eng_word):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO words(rus, eng)
            VALUES(%s, %s)
            ON CONFLICT (rus) DO NOTHING
            RETURNING id, rus, eng""", (rus_word, eng_word))
        new_word = cur.fetchone()
        print(f'Добавлена пара слов {new_word}')


if __name__ == '__main__':
    try:
        with psycopg2.connect(database=os.getenv('DB_NAME'), user=os.getenv('DB_USER'),
                              password=os.getenv('DB_PASS')) as conn:

            create_tables(conn)

            for rus, eng in start_words.items():
                insert_start_words(conn, rus_word=rus, eng_word=eng)

            conn.commit()
    except Exception as error:
        print(f"Ошибка: {error}")
