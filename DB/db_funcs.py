import psycopg2
from dotenv import load_dotenv
import os


load_dotenv()


def add_connect():
    connection = psycopg2.connect(
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'))
    return connection


def check_user(tg_id):
    with add_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT id FROM users
                        WHERE tg_id = %s
                        """, (tg_id,))
            return cur.fetchone()


def add_user(tg_id):
    with add_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                            INSERT INTO users (tg_id)
                            VALUES (%s)
                            ON CONFLICT (tg_id) DO NOTHING
                            RETURNING id, tg_id
                            """, (tg_id,))
            user = cur.fetchone()
            if user:
                print(f'Добавлен пользователь с ID: {user[0]}')
        conn.commit()
        return user


def get_target_word(tg_id):
    with add_connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                            SELECT words.id, rus,eng FROM words
                            LEFT JOIN users_words ON words.id = users_words.id_word
                            WHERE users_words.id_word IS NULL OR users_words.id_user = %s
                            ORDER BY RANDOM() LIMIT 1;
                            """, (tg_id,))
                row = cur.fetchone()
                if row:
                    return row[1], row[2]
                else:
                    print('Таблица пуста')
            except psycopg2.Error as e:
                print(f'Ошибка при выполнении запроса: {e}')


def get_other_words_for_answer(tg_id, target_word):
    with add_connect() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                        SELECT rus, eng FROM words
                        LEFT JOIN users_words ON words.id = users_words.id_word
                        WHERE (users_words.id_word IS NULL OR users_words.id_user = %s) AND rus != %s 
                        ORDER BY RANDOM() LIMIT 3;
                        """, (tg_id, target_word,))
            rows = cur.fetchall()
            return [row[1] for row in rows]


def add_user_words(rus, eng, tg_id):
    user = check_user(tg_id)
    if user is None:
        user_info = add_user(tg_id)
        if user_info is None:
            return False
        user_id = user_info[0]
    else:
        user_id = user[0]

    with add_connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO words(rus, eng) 
                    VALUES(%s, %s)
                    ON CONFLICT (rus) DO NOTHING
                    RETURNING id
                """, (rus, eng))

                word_id = cur.fetchone()

                if not word_id:
                    print(f'Слово уже существует')
                    return False

                cur.execute("""
                    INSERT INTO users_words (id_user, id_word) 
                    VALUES (%s, %s);
                """, (user_id, word_id[0]))

                print(f'Добавлена новая пара слов')
                conn.commit()
                return True

            except Exception as e:
                print(f"Ошибка при добавлении слов: {e}")
                return False

def delete_words(word, tg_id):
    user = check_user(tg_id)
    if user is None:
        user_info = add_user(tg_id)
        if user_info is None:
            return False
        user_id = user_info[0]
    else:
        user_id = user[0]
        
    with add_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(""" 
                SELECT id FROM words
                WHERE rus = %s OR eng = %s
            """, (word, word))
            word_id = cur.fetchone()

            if word_id is not None:
                word_id = word_id[0]

                cur.execute("""
                    SELECT * FROM users_words
                    WHERE id_user = %s AND id_word = %s
                """, (user_id, word_id))

                user_word = cur.fetchone()
                if user_word is not None:
                    cur.execute("""
                        DELETE FROM users_words
                        WHERE id_user = %s AND id_word = %s
                    """, (user_id, word_id))

                    cur.execute("""
                        DELETE FROM words
                        WHERE id = %s
                    """, (word_id,))

                    print(f'Удалено слово')
                    conn.commit()
                    return True
                else:
                    print(f'Слово "{word}" не найдено у пользователя с id {user_id}')
                    return False
            else:
                print(f'Слово "{word}" не найдено в базе данных')
                return False

