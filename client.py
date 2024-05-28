import grpc
import x_pb2
import x_pb2_grpc

def run():
    channel = grpc.insecure_channel('localhost:50051')
    stub = x_pb2_grpc.XServiceStub(channel)
    token = ""

    def display_logged_in_menu():
        print("\nOpcje po zalogowaniu:")
        print("3. Wyślij wiadomość")
        print("4. Pobierz wiadomości")
        print("5. Polub wiadomość")
        print("6. Skomentuj wiadomość")
        print("7. Śledź użytkownika")
        print("8. Wyświetl ostatnie 10 wiadomości")
        print("9. Edytuj wiadomość")
        print("10. Ustawienia konta")
        print("11. Wyloguj się")

    def display_account_settings_menu():
        print("\nUstawienia konta:")
        print("1. Zmień hasło")
        print("2. Usuń konto")
        print("3. Powrót do głównego menu")
        choice = input("Wybierz opcję: ")
        return choice

    while True:
        if not token:
            print("1. Rejestracja")
            print("2. Logowanie")
            choice = input("Wybierz opcję: ")

            if choice == '1':
                # Rejestracja użytkownika
                username = input("Nazwa użytkownika: ")
                password = input("Hasło: ")
                response = stub.RegisterUser(x_pb2.RegisterUserRequest(username=username, password=password))
                print(response.message)
                if response.success:
                    response = stub.LoginUser(x_pb2.LoginUserRequest(username=username, password=password))
                    if response.success:
                        token = response.token
                        print("Zalogowano po rejestracji. Token:", token)
                        display_logged_in_menu()
            elif choice == '2':
                # Logowanie użytkownika
                username = input("Nazwa użytkownika: ")
                password = input("Hasło: ")
                response = stub.LoginUser(x_pb2.LoginUserRequest(username=username, password=password))
                if response.success:
                    token = response.token
                    print("Zalogowano. Token:", token)
                    display_logged_in_menu()
                else:
                    print(response.message)
            else:
                print("Nieprawidłowa opcja.")
        else:
            choice = input("Wybierz opcję: ")

            if choice == '3':
                # Wysłanie wiadomości
                message = input("Wiadomość: ")
                response = stub.SendMessage(x_pb2.SendMessageRequest(message=message, user_token=token))
                print(response.message)
            elif choice == '4':
                # Pobranie wiadomości
                count = int(input("Ile wiadomości pobrać: "))
                response = stub.GetMessages(x_pb2.GetMessagesRequest(count=count))
                for msg in response.messages:
                    print(f"ID użytkownika: {msg.username}")
                    print(f"ID wiadomości: {msg.id}")
                    print(f"Wiadomość: {msg.content}")
                    print(f"Data i czas: {msg.timestamp}")
                    print(f"Liczba polubień: {msg.likes}")
                    print(f"Liczba komentarzy: {msg.comments_count}")
                    for comment in msg.comments:
                        print(f"  Komentarz od {comment.username}: {comment.content}")
                    print()
            elif choice == '5':
                # Polubienie wiadomości
                try:
                    message_id = int(input("ID wiadomości do polubienia: "))
                    response = stub.LikeMessage(x_pb2.LikeMessageRequest(message_id=message_id, user_token=token))
                    print(response.message)
                except ValueError:
                    print("ID wiadomości musi być liczbą całkowitą.")
            elif choice == '6':
                # Skomentowanie wiadomości
                try:
                    message_id = int(input("ID wiadomości do skomentowania: "))
                    comment = input("Komentarz: ")
                    response = stub.CommentMessage(x_pb2.CommentMessageRequest(message_id=message_id, comment=comment, user_token=token))
                    print(response.message)
                except ValueError:
                    print("ID wiadomości musi być liczbą całkowitą.")
            elif choice == '7':
                # Śledzenie użytkownika
                username_to_follow = input("Nazwa użytkownika do śledzenia: ")
                response = stub.GetUserId(x_pb2.GetUserIdRequest(username=username_to_follow))
                if response.success:
                    followee_id = response.user_id
                    follow_response = stub.FollowUser(x_pb2.FollowUserRequest(user_token=token, followee_id=followee_id))
                    print(follow_response.message)
                else:
                    print(response.message)
            elif choice == '8':
                # Wyświetlenie ostatnich 10 wiadomości
                response = stub.GetLastMessages(x_pb2.LastMessagesRequest(count=10))
                for msg in response.messages:
                    print(f"ID użytkownika: {msg.username}")
                    print(f"ID wiadomości: {msg.id}")
                    print(f"Wiadomość: {msg.content}")
                    print(f"Data i czas: {msg.timestamp}")
                    print(f"Liczba polubień: {msg.likes}")
                    print(f"Liczba komentarzy: {msg.comments_count}")
                    for comment in msg.comments:
                        print(f"  Komentarz od {comment.username}: {comment.content}")
                    print()
            elif choice == '9':
                # Edytowanie wiadomości
                try:
                    message_id = int(input("ID wiadomości do edytowania: "))
                    new_content = input("Nowa treść wiadomości: ")
                    response = stub.EditMessage(x_pb2.EditMessageRequest(message_id=message_id, new_content=new_content, user_token=token))
                    print(response.message)
                except ValueError:
                    print("ID wiadomości musi być liczbą całkowitą.")
            elif choice == '10':
                # Ustawienia konta
                while True:
                    sub_choice = display_account_settings_menu()
                    if sub_choice == '1':
                        # Zmiana hasła
                        old_password = input("Stare hasło: ")
                        new_password = input("Nowe hasło: ")
                        response = stub.ChangePassword(x_pb2.ChangePasswordRequest(user_token=token, old_password=old_password, new_password=new_password))
                        print(response.message)
                    elif sub_choice == '2':
                        # Usunięcie konta
                        delete_messages = input("Czy chcesz usunąć wszystkie swoje wiadomości? (tak/nie): ").lower() == 'tak'
                        response = stub.DeleteAccount(x_pb2.DeleteAccountRequest(user_token=token, delete_messages=delete_messages))
                        print(response.message)
                        if response.success:
                            token = ""
                            break
                    elif sub_choice == '3':
                        # Powrót do głównego menu
                        break
                    else:
                        print("Nieprawidłowa opcja.")
            elif choice == '11':
                # Wylogowanie użytkownika
                token = ""
                print("Wylogowano.")
            else:
                print("Nieprawidłowa opcja.")
                
            if token:
                display_logged_in_menu()

if __name__ == '__main__':
    run()
