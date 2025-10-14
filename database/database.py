import firebase_admin
from firebase_admin import credentials,firestore
from config import Config
# este es solo para conextarse a firebase
class FirebaseConfig:
    _db=None

    @classmethod
    def get_db(cls):#usa el patron singleton si no existe la crea y si ya esxiste la usa
        if cls._db is None:
            cls._initialize_firebase()
        return cls._db
    @classmethod
    def _initialize_firebase(cls):
        try:
            firebase_admin.get_app()
            print("ya se conecto a firebase")
        except ValueError:
            print("inicializando firebase")
            cred=credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)

            firebase_admin.initialize_app(cred,{'projectID': Config.FIREBASE_PROJECT_ID})
            print("ya se inicializo")
        cls._db=firestore.client()
        print("conexion a fb")
