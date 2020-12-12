import psycopg2
from psycopg2.extras import RealDictCursor

from config import *


def establish_connection():
    connection = psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=RealDictCursor)
    cursor = connection.cursor()
    return connection, cursor


def user_insert(user_id):
    connection, cursor = establish_connection()
    try:
        cursor.execute("INSERT INTO tg_users(tg_id) VALUES (%(user_id)s)", {'user_id': user_id})
        connection.commit()
    except:
        connection.rollback()
    connection.close()


def delete_from_control_points(user_id):
    connection, cursor = establish_connection()
    cursor.execute("DELETE FROM control_points WHERE tg_id = %(user_id)s", {'user_id': user_id})
    connection.commit()
    connection.close()


def insert_new_control_points(user_id, tables, trimester):
    connection, cursor = establish_connection()
    cursor.execute("UPDATE tg_users SET trimester = %(trimester)s WHERE tg_id = %(user_id)s", {'trimester': trimester, 'user_id': user_id})
    for subject in tables.keys():
        table_array = tables[subject]
        for table in table_array:
            cursor.execute("INSERT INTO control_points(tg_id, subject, control_point, current_mark, passing_mark, max_mark, date) "
                           "VALUES (%(user_id)s, %(subject)s,%(control_point)s,%(current_mark)s,%(passing_mark)s,%(max_mark)s,%(date)s)",
                           {'user_id': user_id,
                            'subject': subject,
                            'control_point': table['control_point'],
                            'current_mark': table['current_mark'],
                            'passing_mark': table['passing_mark'],
                            'max_mark': table['max_mark'],
                            'date': table['date']})
    connection.commit()
    connection.close()


def get_tables_and_trimester(user_id):
    tables = {}
    connection, cursor = establish_connection()
    cursor.execute("SELECT trimester FROM tg_users WHERE tg_id = %(user_id)s", {'user_id': user_id})
    trimester = cursor.fetchone()['trimester']

    cursor.execute("SELECT DISTINCT subject FROM control_points WHERE tg_id = %(user_id)s", {'user_id': user_id})
    subjects = cursor.fetchall()
    for subject in subjects:
        tables[subject['subject']] = []

    cursor.execute("SELECT subject, control_point, current_mark, passing_mark, max_mark, date FROM control_points WHERE tg_id = %(user_id)s", {'user_id': user_id})
    rows = cursor.fetchall()
    for row in rows:
        tables[row['subject']].append({'control_point': row['control_point'],
                                       'current_mark': row['current_mark'],
                                       'passing_mark': row['passing_mark'],
                                       'max_mark': row['max_mark'],
                                       'date': row['date']})
    connection.close()
    return tables, trimester


def update_current_mark(user_id, subject, control_point, new_mark, new_date):
    connection, cursor = establish_connection()
    cursor.execute("UPDATE control_points SET current_mark = %(current_mark)s, date = %(date)s WHERE tg_id=%(user_id)s AND subject = %(subject)s AND control_point = %(control_point)s",
                   {'current_mark': new_mark,
                    'date': new_date,
                    'subject': subject,
                    'control_point': control_point,
                    'user_id': user_id})
    connection.commit()
    connection.close()


def set_msg_ids(user_id, login_msg_id, password_msg_id):
    connection, cursor = establish_connection()
    cursor.execute("UPDATE tg_users SET login_message_id = %(login_msg_id)s, password_message_id = %(password_msg_id)s WHERE tg_id=%(user_id)s", {'login_msg_id': login_msg_id, 'password_msg_id': password_msg_id, 'user_id': user_id})
    connection.commit()
    connection.close()


def delete_msg_ids(user_id):
    connection, cursor = establish_connection()
    cursor.execute("UPDATE tg_users SET login_message_id = NULL, password_message_id =NULL WHERE tg_id=%(user_id)s", {'user_id': user_id})
    connection.commit()
    connection.close()


def get_active_users():
    connection, cursor = establish_connection()
    cursor.execute("SELECT tg_id, login_message_id, password_message_id, trimester FROM tg_users WHERE login_message_id IS NOT NULL AND password_message_id IS NOT NULL")
    fetches = cursor.fetchall()
    connection.close()
    return fetches
