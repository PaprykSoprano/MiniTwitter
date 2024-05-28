import grpc
from concurrent import futures
import mysql.connector
import x_pb2
import x_pb2_grpc
import hashlib
import secrets

# Konfiguracja bazy danych
DATABASE_CONFIG = {
    'user': 'xuser',
    'password': 'password',
    'host': 'localhost',
    'database': 'x'
}

class XServiceServicer(x_pb2_grpc.XServiceServicer):
    def __init__(self):
        self.conn = mysql.connector.connect(**DATABASE_CONFIG)
        self.cursor = self.conn.cursor()

    # Metoda do hashowania hasła użytkownika
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    # Rejestracja nowego użytkownika
    def RegisterUser(self, request, context):
        username = request.username
        password = request.password
        password_hash = self.hash_password(password)

        try:
            self.cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
            self.conn.commit()
            return x_pb2.RegisterUserResponse(success=True, message="Rejestracja udana.")
        except mysql.connector.IntegrityError:
            return x_pb2.RegisterUserResponse(success=False, message="Nazwa użytkownika już istnieje.")

    # Logowanie użytkownika
    def LoginUser(self, request, context):
        username = request.username
        password = request.password
        password_hash = self.hash_password(password)

        self.cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = self.cursor.fetchone()
        if not user:
            return x_pb2.LoginUserResponse(success=False, token="", message="Użytkownik nie istnieje.")
        
        self.cursor.execute("SELECT id FROM users WHERE username = %s AND password_hash = %s", (username, password_hash))
        user = self.cursor.fetchone()
        if user:
            token = secrets.token_hex(16)
            self.cursor.execute("UPDATE users SET token = %s WHERE id = %s", (token, user[0]))
            self.conn.commit()
            return x_pb2.LoginUserResponse(success=True, token=token, message="Zalogowano.")
        else:
            return x_pb2.LoginUserResponse(success=False, token="", message="Złe hasło.")

    # Zmiana hasła użytkownika
    def ChangePassword(self, request, context):
        token = request.user_token
        old_password = request.old_password
        new_password = request.new_password
        old_password_hash = self.hash_password(old_password)
        new_password_hash = self.hash_password(new_password)

        self.cursor.execute("SELECT id FROM users WHERE token = %s AND password_hash = %s", (token, old_password_hash))
        user = self.cursor.fetchone()
        if user:
            self.cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_password_hash, user[0]))
            self.conn.commit()
            return x_pb2.ChangePasswordResponse(success=True, message="Hasło zostało zmienione.")
        else:
            return x_pb2.ChangePasswordResponse(success=False, message="Stare hasło jest niepoprawne.")

    # Wysłanie wiadomości przez użytkownika
    def SendMessage(self, request, context):
        token = request.user_token
        message = request.message

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        user = self.cursor.fetchone()
        if user:
            self.cursor.execute("INSERT INTO messages (user_id, content) VALUES (%s, %s)", (user[0], message))
            self.conn.commit()
            return x_pb2.SendMessageResponse(success=True, message="Wiadomość wysłana.")
        else:
            return x_pb2.SendMessageResponse(success=False, message="Nieautoryzowany użytkownik.")

    # Pobranie określonej liczby wiadomości
    def GetMessages(self, request, context):
        count = request.count
        self.cursor.execute("""
            SELECT messages.id, users.username, messages.content, messages.timestamp,
                   (SELECT COUNT(*) FROM likes WHERE likes.message_id = messages.id) AS likes,
                   (SELECT COUNT(*) FROM comments WHERE comments.message_id = messages.id) AS comments_count
            FROM messages
            JOIN users ON messages.user_id = users.id
            ORDER BY messages.timestamp DESC
            LIMIT %s
        """, (count,))
        messages = self.cursor.fetchall()
        message_list = []
        for msg in messages:
            self.cursor.execute("SELECT users.username, comments.content FROM comments JOIN users ON comments.user_id = users.id WHERE comments.message_id = %s", (msg[0],))
            comments = self.cursor.fetchall()
            comments_list = [x_pb2.Comment(username=comment[0], content=comment[1]) for comment in comments]
            message_list.append(x_pb2.Message(
                id=msg[0],
                username=msg[1],
                content=msg[2],
                timestamp=str(msg[3]),  # Ensure timestamp is converted to string
                likes=msg[4],
                comments_count=msg[5],
                comments=comments_list
            ))
        return x_pb2.GetMessagesResponse(messages=message_list)

    # Pobranie ostatnich wiadomości
    def GetLastMessages(self, request, context):
        count = request.count
        self.cursor.execute("""
            SELECT messages.id, users.username, messages.content, messages.timestamp,
                   (SELECT COUNT(*) FROM likes WHERE likes.message_id = messages.id) AS likes,
                   (SELECT COUNT(*) FROM comments WHERE comments.message_id = messages.id) AS comments_count
            FROM messages
            JOIN users ON messages.user_id = users.id
            ORDER BY messages.timestamp DESC
            LIMIT %s
        """, (count,))
        messages = self.cursor.fetchall()
        message_list = []
        for msg in messages:
            self.cursor.execute("SELECT users.username, comments.content FROM comments JOIN users ON comments.user_id = users.id WHERE comments.message_id = %s", (msg[0],))
            comments = self.cursor.fetchall()
            comments_list = [x_pb2.Comment(username=comment[0], content=comment[1]) for comment in comments]
            message_list.append(x_pb2.Message(
                id=msg[0],
                username=msg[1],
                content=msg[2],
                timestamp=str(msg[3]),  # Ensure timestamp is converted to string
                likes=msg[4],
                comments_count=msg[5],
                comments=comments_list
            ))
        return x_pb2.LastMessagesResponse(messages=message_list)

    # Polubienie wiadomości przez użytkownika
    def LikeMessage(self, request, context):
        token = request.user_token
        message_id = request.message_id

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        user = self.cursor.fetchone()
        if user:
            self.cursor.execute("SELECT id FROM messages WHERE id = %s", (message_id,))
            message = self.cursor.fetchone()
            if not message:
                return x_pb2.LikeMessageResponse(success=False, message="Wiadomość nie istnieje.")
            
            self.cursor.execute("SELECT id FROM likes WHERE user_id = %s AND message_id = %s", (user[0], message_id))
            existing_like = self.cursor.fetchone()
            if existing_like:
                return x_pb2.LikeMessageResponse(success=False, message="Już polubiłeś tę wiadomość.")
            try:
                self.cursor.execute("INSERT INTO likes (user_id, message_id) VALUES (%s, %s)", (user[0], message_id))
                self.conn.commit()
                return x_pb2.LikeMessageResponse(success=True, message="Wiadomość polubiona.")
            except mysql.connector.IntegrityError:
                return x_pb2.LikeMessageResponse(success=False, message="Błąd przy polubieniu wiadomości.")
        else:
            return x_pb2.LikeMessageResponse(success=False, message="Nieautoryzowany użytkownik.")

    # Dodanie komentarza do wiadomości
    def CommentMessage(self, request, context):
        token = request.user_token
        message_id = request.message_id
        comment = request.comment

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        user = self.cursor.fetchone()
        if user:
            self.cursor.execute("SELECT id FROM messages WHERE id = %s", (message_id,))
            message = self.cursor.fetchone()
            if not message:
                return x_pb2.CommentMessageResponse(success=False, message="Wiadomość nie istnieje.")
            
            self.cursor.execute("INSERT INTO comments (user_id, message_id, content) VALUES (%s, %s, %s)", (user[0], message_id, comment))
            self.conn.commit()
            return x_pb2.CommentMessageResponse(success=True, message="Komentarz dodany.")
        else:
            return x_pb2.CommentMessageResponse(success=False, message="Nieautoryzowany użytkownik.")

    # Śledzenie innego użytkownika
    def FollowUser(self, request, context):
        token = request.user_token
        followee_id = request.followee_id

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        follower = self.cursor.fetchone()
        if follower:
            self.cursor.execute("SELECT id FROM follows WHERE follower_id = %s AND followee_id = %s", (follower[0], followee_id))
            existing_follow = self.cursor.fetchone()
            if existing_follow:
                return x_pb2.FollowUserResponse(success=False, message="Już śledzisz tego użytkownika.")
            try:
                self.cursor.execute("INSERT INTO follows (follower_id, followee_id) VALUES (%s, %s)", (follower[0], followee_id))
                self.conn.commit()
                return x_pb2.FollowUserResponse(success=True, message="Użytkownik śledzony.")
            except mysql.connector.IntegrityError:
                return x_pb2.FollowUserResponse(success=False, message="Błąd przy śledzeniu użytkownika.")
        else:
            return x_pb2.FollowUserResponse(success=False, message="Nieautoryzowany użytkownik.")

    # Pobranie ID użytkownika na podstawie nazwy użytkownika
    def GetUserId(self, request, context):
        username = request.username
        self.cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user = self.cursor.fetchone()
        if user:
            return x_pb2.GetUserIdResponse(user_id=user[0], success=True, message="Znaleziono użytkownika.")
        else:
            return x_pb2.GetUserIdResponse(user_id=0, success=False, message="Nie znaleziono użytkownika.")

    # Edytowanie wiadomości przez autora
    def EditMessage(self, request, context):
        token = request.user_token
        message_id = request.message_id
        new_content = request.new_content

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        user = self.cursor.fetchone()
        if user:
            self.cursor.execute("SELECT user_id FROM messages WHERE id = %s", (message_id,))
            message = self.cursor.fetchone()
            if message and message[0] == user[0]:
                self.cursor.execute("UPDATE messages SET content = %s WHERE id = %s", (new_content, message_id))
                self.conn.commit()
                return x_pb2.EditMessageResponse(success=True, message="Wiadomość zaktualizowana.")
            else:
                return x_pb2.EditMessageResponse(success=False, message="Nieautoryzowany użytkownik lub wiadomość nie istnieje.")
        else:
            return x_pb2.EditMessageResponse(success=False, message="Nieautoryzowany użytkownik.")

    # Usuwanie wiadomości przez autora
    def DeleteMessage(self, request, context):
        token = request.user_token
        message_id = request.message_id

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        user = self.cursor.fetchone()
        if user:
            self.cursor.execute("DELETE FROM comments WHERE message_id = %s", (message_id,))
            self.cursor.execute("DELETE FROM likes WHERE message_id = %s", (message_id,))
            self.cursor.execute("DELETE FROM messages WHERE id = %s AND user_id = %s", (message_id, user[0]))
            self.conn.commit()
            return x_pb2.DeleteMessageResponse(success=True, message="Wiadomość usunięta.")
        else:
            return x_pb2.DeleteMessageResponse(success=False, message="Nieautoryzowany użytkownik.")

    # Usuwanie konta użytkownika (z opcją usunięcia wszystkich wiadomości)
    def DeleteAccount(self, request, context):
        token = request.user_token
        delete_messages = request.delete_messages

        self.cursor.execute("SELECT id FROM users WHERE token = %s", (token,))
        user = self.cursor.fetchone()
        if user:
            user_id = user[0]
            if delete_messages:
                self.cursor.execute("DELETE FROM comments WHERE message_id IN (SELECT id FROM messages WHERE user_id = %s)", (user_id,))
                self.cursor.execute("DELETE FROM likes WHERE message_id IN (SELECT id FROM messages WHERE user_id = %s)", (user_id,))
                self.cursor.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
            self.cursor.execute("DELETE FROM likes WHERE user_id = %s", (user_id,))
            self.cursor.execute("DELETE FROM comments WHERE user_id = %s", (user_id,))
            self.cursor.execute("DELETE FROM follows WHERE follower_id = %s OR followee_id = %s", (user_id, user_id))
            self.cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            self.conn.commit()
            return x_pb2.DeleteAccountResponse(success=True, message="Konto i wiadomości użytkownika usunięte." if delete_messages else "Konto użytkownika usunięte, wiadomości zachowane.")
        else:
            return x_pb2.DeleteAccountResponse(success=False, message="Nieautoryzowany użytkownik.")

# Funkcja uruchamiająca serwer
def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    x_pb2_grpc.add_XServiceServicer_to_server(XServiceServicer(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Serwer został poprawnie uruchomiony.")
    return server

if __name__ == '__main__':
    server = serve()
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\nSerwer zatrzymany.")
